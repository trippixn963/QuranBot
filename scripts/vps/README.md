# QuranBot VPS Management System

A comprehensive system for managing QuranBot on a VPS, providing tools for bot control, log management, and backups.

## 📁 Directory Structure

```
scripts/vps/
├── config/                    # ⚙️ Configuration
│   └── vps_config.json       # Main configuration file
├── core/                     # 🔧 Core Management System
│   ├── __init__.py          # Package initialization
│   ├── vps_manager.py       # Main VPS management class
│   ├── log_manager.py       # Log management functionality
│   └── backup_manager.py    # Backup functionality
├── scripts/                  # 🚀 Platform-specific Scripts
│   ├── windows/             # Windows PowerShell scripts
│   │   ├── start.ps1       # Start bot
│   │   ├── stop.ps1        # Stop bot
│   │   ├── restart.ps1     # Restart bot
│   │   ├── status.ps1      # Check bot status
│   │   └── logs.ps1        # Log management
│   └── linux/              # Linux shell scripts
│       ├── start.sh        # Start bot
│       ├── stop.sh         # Stop bot
│       ├── restart.sh      # Restart bot
│       ├── status.sh       # Check bot status
│       └── logs.sh         # Log management
└── ui/                      # 🖥️ User Interfaces
    ├── cli.py              # Command-line interface
    └── tui.py              # Terminal user interface
```

## 🚀 Quick Start

1. Configure VPS settings in `config/vps_config.json`
2. Set up SSH key authentication with your VPS
3. Run the appropriate script for your platform:

### Windows
```powershell
# Using PowerShell scripts
.\scripts\windows\start.ps1    # Start bot
.\scripts\windows\stop.ps1     # Stop bot
.\scripts\windows\restart.ps1  # Restart bot
.\scripts\windows\status.ps1   # Check status
.\scripts\windows\logs.ps1     # Manage logs
```

### Linux/Mac
```bash
# Using shell scripts
./scripts/linux/start.sh     # Start bot
./scripts/linux/stop.sh      # Stop bot
./scripts/linux/restart.sh   # Restart bot
./scripts/linux/status.sh    # Check status
./scripts/linux/logs.sh      # Manage logs
```

### Python Interfaces
```bash
# Command-line interface
python -m scripts.vps.ui.cli bot start
python -m scripts.vps.ui.cli logs view --lines 100
python -m scripts.vps.ui.cli backup create

# Terminal user interface
python -m scripts.vps.ui.tui
```

## ⚙️ Configuration

The system is configured through `config/vps_config.json`. Key settings include:

- VPS connection details (host, user, SSH key)
- Bot service configuration
- Monitoring thresholds
- Logging preferences
- Backup settings

Example configuration:
```json
{
    "vps": {
        "host": "your.vps.ip",
        "user": "root",
        "ssh_key": "~/.ssh/your_key"
    },
    "bot": {
        "service_name": "quranbot",
        "install_path": "/opt/quranbot"
    }
}
```

## 🔧 Core Features

### Bot Control
- Start/stop/restart bot service
- Check bot status and health
- Monitor system resources

### Log Management
- View real-time logs
- Download log files
- Analyze log patterns
- Clean up old logs

### Backup System
- Create full/partial backups
- List available backups
- Restore from backup
- Auto-cleanup old backups

## 🖥️ User Interfaces

### Command-Line Interface (CLI)
The CLI provides direct command execution:

```bash
# Bot control
python -m scripts.vps.ui.cli bot start
python -m scripts.vps.ui.cli bot stop
python -m scripts.vps.ui.cli bot restart
python -m scripts.vps.ui.cli bot status

# Log management
python -m scripts.vps.ui.cli logs view --lines 100
python -m scripts.vps.ui.cli logs download --date 2024-01-01
python -m scripts.vps.ui.cli logs analyze
python -m scripts.vps.ui.cli logs cleanup --days 30

# Backup management
python -m scripts.vps.ui.cli backup create --name my_backup
python -m scripts.vps.ui.cli backup list
python -m scripts.vps.ui.cli backup restore my_backup
python -m scripts.vps.ui.cli backup cleanup --days 30
```

### Terminal User Interface (TUI)
The TUI provides an interactive menu-driven interface:

```bash
python -m scripts.vps.ui.tui
```

Features:
- Easy-to-use menu system
- Real-time feedback
- Colorized output
- Interactive prompts

## 🔒 Security

1. Use SSH key authentication only
2. Keep your SSH key secure
3. Use a non-root user with sudo privileges
4. Regularly update VPS and bot
5. Monitor logs for suspicious activity

## 📋 Maintenance

Regular maintenance tasks:

1. Monitor system resources
2. Check log files for errors
3. Create regular backups
4. Clean up old logs/backups
5. Update bot and dependencies

## 🐛 Troubleshooting

Common issues and solutions:

1. SSH Connection Failed
   - Check SSH key permissions
   - Verify VPS IP and port
   - Ensure SSH service is running

2. Bot Won't Start
   - Check service status
   - Review error logs
   - Verify permissions

3. Backup Failed
   - Check disk space
   - Verify backup paths
   - Check file permissions

## 📚 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details. 