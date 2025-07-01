# 🚀 Quran Bot Setup Guide

## Prerequisites

### 1. Python 3.8+
Make sure you have Python 3.8 or higher installed:
```bash
python --version
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. Install FFmpeg

#### Windows:
1. **Download FFmpeg:**
   - Go to [FFmpeg Downloads](https://ffmpeg.org/download.html)
   - Click "Windows Builds" 
   - Download the latest release (e.g., "ffmpeg-master-latest-win64-gpl.zip")

2. **Extract and Install:**
   - Extract the ZIP file to a folder (e.g., `C:\ffmpeg`)
   - Add FFmpeg to your PATH:
     - Open System Properties → Advanced → Environment Variables
     - Edit the "Path" variable
     - Add `C:\ffmpeg\bin` to the path
     - Click OK to save

3. **Verify Installation:**
   - Open a new Command Prompt
   - Run: `ffmpeg -version`

#### Alternative: Using Chocolatey (Windows)
```bash
choco install ffmpeg
```

#### Alternative: Using Scoop (Windows)
```bash
scoop install ffmpeg
```

#### macOS:
```bash
brew install ffmpeg
```

#### Linux (Ubuntu/Debian):
```bash
sudo apt update
sudo apt install ffmpeg
```

#### Linux (CentOS/RHEL):
```bash
sudo yum install ffmpeg
```

## Running the Bot

### Option 1: Simple Bot (Recommended for Windows)
```bash
python run_simple.py
```

### Option 2: Full Featured Bot
```bash
python start.py
```

### Option 3: Direct Execution
```bash
python simple_bot.py
```

### Option 4: Windows Batch File
Double-click `start.bat`

## Bot Configuration

### Discord Bot Setup

1. **Create a Discord Application:**
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Click "New Application"
   - Give it a name (e.g., "Quran Bot")

2. **Create a Bot:**
   - Go to the "Bot" section
   - Click "Add Bot"
   - Copy the bot token

3. **Set Bot Permissions:**
   - Go to OAuth2 → URL Generator
   - Select "bot" scope
   - Select these permissions:
     - Send Messages
     - Use Slash Commands
     - Connect
     - Speak
     - Use Voice Activity
   - Copy the generated URL and invite the bot to your server

4. **Update Bot Token:**
   - Edit `simple_bot.py` or `config.py`
   - Replace the token with your bot token

## Troubleshooting

### Common Issues

**"FFmpeg is not installed"**
- Follow the FFmpeg installation guide above
- Make sure to restart your terminal after adding FFmpeg to PATH

**"discord.py is not installed"**
```bash
pip install discord.py
```

**Bot doesn't join voice channel**
- Check if the bot has "Connect" and "Speak" permissions
- Make sure you're in a voice channel when using `/join`

**No audio/stream not working**
- Verify FFmpeg is installed: `ffmpeg -version`
- Check if the stream URL is accessible
- Look at the logs for error messages

**Commands not working**
- Ensure the bot has "Use Slash Commands" permission
- Wait a few minutes after starting the bot for commands to sync

### Testing Without FFmpeg

If you want to test the bot without FFmpeg first, you can temporarily modify the stream URL in `simple_bot.py`:

```python
# Change this line in simple_bot.py
self.quran_stream_url = "https://stream.quran.com:8000/arabic"
# To this:
self.quran_stream_url = "https://httpbin.org/stream/1"  # Test URL
```

## Bot Commands

Once the bot is running, use these slash commands in your Discord server:

- `/join` - Start streaming Quran in your voice channel
- `/leave` - Stop streaming and leave voice channel
- `/status` - Check current streaming status
- `/help` - Show bot information and commands

## 24/7 Hosting

### Using a VPS/Server
1. Upload bot files to your server
2. Install dependencies: `pip install -r requirements.txt`
3. Install FFmpeg: `sudo apt install ffmpeg`
4. Run with screen:
   ```bash
   screen -S quranbot
   python run_simple.py
   # Press Ctrl+A, then D to detach
   ```

### Using PM2
```bash
npm install -g pm2
pm2 start run_simple.py --name quranbot --interpreter python
pm2 save
pm2 startup
```

## Support

If you encounter any issues:
1. Check the logs in `quran_bot.log`
2. Verify all dependencies are installed
3. Ensure FFmpeg is in your PATH
4. Check Discord bot permissions

The bot is designed to be robust and will automatically reconnect if the stream is interrupted. 