# QuranBot VPS Manager

This directory contains scripts to manage your QuranBot deployment on the VPS.

## Configuration

Your VPS information is configured in the scripts:

- **VPS IP**: `159.89.90.90`
- **SSH User**: `root`
- **SSH Key**: `quranbot_key` (located at `C:/Users/hanna/Documents/QuranBot/quranbot_key`)
- **Bot Directory**: `/home/QuranAudioBot`

## Available Scripts

### 1. Python Script (`vps_manager.py`)
A comprehensive Python script with all VPS management features.

**Usage:**
```bash
# Interactive menu
python vps_manager.py menu

# Direct commands
python vps_manager.py status
python vps_manager.py start
python vps_manager.py stop
python vps_manager.py restart
python vps_manager.py deploy
python vps_manager.py logs --lines 100
python vps_manager.py upload --audio-path "C:/path/to/audio"
python vps_manager.py backup
python vps_manager.py setup
python vps_manager.py check
```

### 2. Windows Batch Script (`vps_manager.bat`)
A Windows batch file for easy VPS management.

**Usage:**
```cmd
# Run the script
vps_manager.bat
```

### 3. PowerShell Script (`vps_manager.ps1`)
A PowerShell script for Windows with better error handling.

**Usage:**
```powershell
# Run the script
.\vps_manager.ps1
```

## Features

### Basic Management
- ✅ **Check Connection**: Test SSH connection to VPS
- ✅ **Get Status**: Check if bot is running and view recent logs
- ✅ **Start Bot**: Start the QuranBot
- ✅ **Stop Bot**: Stop the QuranBot
- ✅ **Restart Bot**: Restart the QuranBot

### Deployment
- ✅ **Deploy**: Pull latest changes from Git and restart bot
- ✅ **Setup Environment**: Initial setup (clone repo, create venv, install deps)

### Monitoring
- ✅ **View Logs**: View bot logs (configurable number of lines)
- ✅ **Upload Audio**: Upload audio files to VPS
- ✅ **Create Backup**: Create timestamped backup of bot files

## Quick Commands

### Check if bot is running:
```bash
ssh -i quranbot_key root@159.89.90.90 "ps aux | grep 'python run.py' | grep -v grep"
```

### View recent logs:
```bash
ssh -i quranbot_key root@159.89.90.90 "tail -20 /home/QuranAudioBot/bot.log"
```

### Restart bot:
```bash
ssh -i quranbot_key root@159.89.90.90 "cd /home/QuranAudioBot && pkill -f 'python run.py' && sleep 2 && source venv/bin/activate && nohup python run.py > bot.log 2>&1 &"
```

### Deploy updates:
```bash
ssh -i quranbot_key root@159.89.90.90 "cd /home/QuranAudioBot && git pull origin main && source venv/bin/activate && pip install -r requirements.txt && pkill -f 'python run.py' && sleep 2 && nohup python run.py > bot.log 2>&1 &"
```

## Configuration File

The `vps_config.json` file contains all the configuration settings. You can edit this file to update paths or add new settings.

## Troubleshooting

### SSH Connection Issues
1. Make sure the SSH key file exists at the specified path
2. Check that the SSH key has correct permissions (600)
3. Verify the VPS IP and username are correct

### Bot Not Starting
1. Check if the virtual environment exists
2. Verify all dependencies are installed
3. Check the bot logs for error messages

### Audio Upload Issues
1. Ensure the local audio path exists
2. Check available disk space on VPS
3. Verify SSH key permissions

## Security Notes

- Keep your SSH key secure and don't share it
- The SSH key should have restricted permissions (600)
- Consider using a non-root user for better security
- Regularly update your VPS and dependencies

## Support

If you encounter issues:
1. Check the bot logs first
2. Verify SSH connectivity
3. Ensure all paths and configurations are correct
4. Check VPS resources (disk space, memory, CPU) 