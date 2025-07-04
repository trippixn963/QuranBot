# QuranBot VPS Manager

A comprehensive SSH-based management tool for controlling the QuranBot on your VPS.

## Features

### Bot Control
- ✅ Check SSH connection to VPS
- ✅ Get bot status and uptime
- ✅ Start/Stop/Restart bot
- ✅ Deploy latest code from git

### Logs & Monitoring
- ✅ View recent bot logs
- ✅ Search logs for specific terms
- ✅ Download all logs to local machine
- ✅ Clear old logs (older than 7 days)

### Backup & Restore
- ✅ Create timestamped backups
- ✅ List available backups
- ✅ Restore from backup
- ✅ Cleanup old backups

### System Management
- ✅ Initial environment setup
- ✅ Continuous bot monitoring
- ✅ System information (CPU, memory, disk)
- ✅ Network status checks
- ✅ System package updates

### Utilities
- ✅ Upload audio files to VPS
- ✅ Force kill Python processes
- ✅ Emergency restart procedures

## Setup

### 1. Install Dependencies

```bash
pip install paramiko
```

### 2. Configure VPS Connection

1. Copy the template config file:
```bash
cp vps_config.json.template vps_config.json
```

2. Edit `vps_config.json` with your VPS details:
```json
{
    "vps_host": "your-vps-ip-or-domain.com",
    "vps_port": 22,
    "vps_username": "your-username",
    "vps_password": "your-password",
    "vps_key_path": "path/to/private/key",
    "bot_directory": "/home/username/QuranBot",
    "backup_directory": "/home/username/QuranBot/backups",
    "logs_directory": "/home/username/QuranBot/logs",
    "audio_directory": "/home/username/QuranBot/audio",
    "local_logs_dir": "./logs",
    "local_audio_dir": "./audio",
    "ssh_timeout": 30,
    "command_timeout": 60
}
```

### 3. Authentication Options

#### Password Authentication
```json
{
    "vps_password": "your-password",
    "vps_key_path": null
}
```

#### SSH Key Authentication (Recommended)
```json
{
    "vps_password": null,
    "vps_key_path": "~/.ssh/id_rsa"
}
```

## Usage

### Via Batch Menu (Windows)
```bash
scripts/quranbot_manager.bat
```
Then select "VPS Manager" and choose your action.

### Direct Command Line
```bash
# Test connection
python scripts/vps/vps_manager.py --check-connection

# Check bot status
python scripts/vps/vps_manager.py --get-bot-status

# Start bot
python scripts/vps/vps_manager.py --start-bot

# View logs
python scripts/vps/vps_manager.py --view-logs

# Create backup
python scripts/vps/vps_manager.py --create-backup

# Deploy latest code
python scripts/vps/vps_manager.py --deploy-bot
```

## Available Commands

| Command | Description |
|---------|-------------|
| `--check-connection` | Test SSH connection to VPS |
| `--get-bot-status` | Check if bot is running and get uptime |
| `--start-bot` | Start the QuranBot on VPS |
| `--stop-bot` | Stop the QuranBot on VPS |
| `--restart-bot` | Stop and restart the bot |
| `--deploy-bot` | Pull latest code and restart |
| `--view-logs` | Show recent bot log entries |
| `--search-logs` | Search logs for specific terms |
| `--download-logs` | Download all log files to local logs folder |
| `--clear-old-logs` | Remove log files older than 7 days |
| `--create-backup` | Create timestamped backup of bot |
| `--list-backups` | Show all available backup files |
| `--restore-backup` | Restore bot from backup file |
| `--cleanup-old-backups` | Remove backups older than 7 days |
| `--setup-environment` | Initial bot setup (first time only) |
| `--monitor-bot` | Continuous monitoring with alerts |
| `--system-info` | CPU, memory, disk usage, uptime |
| `--check-disk-space` | Show disk space on VPS |
| `--check-network-status` | Test internet, DNS, open ports |
| `--upload-audio` | Upload audio files to VPS |
| `--update-system` | Update system packages on VPS |
| `--kill-all-python` | Force kill all Python processes |
| `--emergency-restart` | Force kill and restart everything |

## Security Notes

1. **SSH Key Authentication**: Use SSH keys instead of passwords for better security
2. **Firewall**: Ensure your VPS firewall allows SSH connections
3. **User Permissions**: The VPS user should have sudo access for system operations
4. **Config File**: Keep `vps_config.json` secure and don't commit it to version control

## Troubleshooting

### Connection Issues
- Verify VPS IP/hostname is correct
- Check SSH port (default: 22)
- Ensure SSH service is running on VPS
- Test with `ssh username@hostname` manually

### Permission Issues
- Ensure VPS user has sudo access
- Check file permissions on bot directory
- Verify Python environment is accessible

### Bot Not Starting
- Check Python dependencies are installed
- Verify environment variables are set
- Check bot logs for specific errors
- Ensure bot directory structure is correct

## File Structure

```
scripts/vps/
├── vps_manager.py          # Main VPS management script
├── vps_config.json.template # Configuration template
└── README.md              # This documentation
```

## Error Handling

The VPS manager includes comprehensive error handling:
- Connection timeouts
- Authentication failures
- Command execution errors
- File transfer issues
- Network connectivity problems

All errors are logged with descriptive messages to help with troubleshooting. 