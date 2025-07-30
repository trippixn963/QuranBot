# 🚀 QuranBot Basic Setup Example

This example demonstrates the minimal configuration needed to get QuranBot running for development or small community use.

## 📋 **What's Included**

- **Basic Configuration** - Minimal `.env` file
- **Simple Docker Setup** - One-command deployment
- **Essential Audio** - Sample audio file structure
- **Getting Started Guide** - Step-by-step instructions

## 🏗️ **Directory Structure**

```
basic-setup/
├── README.md                 # This file
├── .env.example             # Basic environment configuration
├── docker-compose.yml       # Simple Docker setup
├── audio/                   # Sample audio structure
│   └── Saad Al Ghamdi/     # Example reciter
│       ├── 001.mp3         # Al-Fatiha
│       ├── 002.mp3         # Al-Baqarah (first few ayahs)
│       └── 114.mp3         # An-Nas
└── config/
    └── basic-config.json    # Minimal bot configuration
```

## ⚡ **Quick Start**

### 1. **Prerequisites**
- Discord bot token ([Get one here](https://discord.com/developers/applications))
- Python 3.11+ OR Docker
- A Discord server where you have admin permissions

### 2. **Configuration**
```bash
# Copy the example configuration
cp .env.example .env

# Edit with your bot details
nano .env
```

Fill in these essential values:
```bash
DISCORD_TOKEN=your_bot_token_here
GUILD_ID=your_server_id_here
TARGET_CHANNEL_ID=your_voice_channel_id_here
ADMIN_USER_ID=your_discord_user_id_here
```

### 3. **Run with Docker** (Recommended)
```bash
# Start the bot
docker-compose up -d

# View logs
docker-compose logs -f quranbot
```

### 4. **Run with Python**
```bash
# Install dependencies
pip install -r ../../requirements.txt

# Run the bot
cd ../..
python main.py
```

## 🎵 **Audio Setup**

### **Option 1: Use Sample Audio**
The basic setup includes sample files for testing. These are short clips for demonstration only.

### **Option 2: Add Your Own Audio**
1. Create reciter folders in `audio/`
2. Add MP3 files named `001.mp3` through `114.mp3`
3. Ensure proper audio quality (128kbps minimum)

```bash
# Example structure
audio/
├── Saad Al Ghamdi/
│   ├── 001.mp3  # Al-Fatiha
│   ├── 002.mp3  # Al-Baqarah
│   └── ...      # Continue through 114.mp3
└── Abdul Basit Abdul Samad/
    ├── 001.mp3
    └── ...
```

## 🤖 **Bot Commands**

Once running, try these commands in your Discord server:

- `/play 1` - Play Surah Al-Fatiha
- `/stop` - Stop current playback
- `/verse 2 255` - Get Ayat al-Kursi (Quran 2:255)
- `/quiz` - Start an Islamic knowledge quiz

## 🔧 **Customization**

### **Change Default Reciter**
```bash
# In .env file
DEFAULT_RECITER=Abdul Basit Abdul Samad
```

### **Adjust Audio Volume**
```bash
# In .env file (0.0 to 1.0)
DEFAULT_VOLUME=0.7
```

### **Set Timezone**
```bash
# For accurate prayer time features
TIMEZONE=America/New_York
```

## 📝 **Troubleshooting**

### **Bot Not Responding**
1. Check bot permissions in Discord server
2. Verify `GUILD_ID` matches your server
3. Ensure bot has "Use Slash Commands" permission

### **Audio Not Playing**
1. Check that `TARGET_CHANNEL_ID` is a voice channel
2. Ensure bot has "Connect" and "Speak" permissions
3. Verify FFmpeg is installed (for non-Docker setup)

### **No Audio Files Found**
1. Check audio folder structure matches expected format
2. Ensure MP3 files are properly named (001.mp3, 002.mp3, etc.)
3. Verify file permissions allow reading

## 🔄 **Next Steps**

Once you have the basic setup working:

1. **Add More Audio**: Download complete Quran recitations
2. **Explore Advanced Features**: Check the `advanced-config/` example
3. **Set up Production**: See the `docker-deployment/` example
4. **Join Community**: [Discord Server](https://discord.gg/syria)

## 📞 **Support**

- **Documentation**: [Main README](../../README.md)
- **Issues**: [GitHub Issues](https://github.com/your-username/QuranBot/issues)
- **Discord**: [Community Server](https://discord.gg/syria)

---

*"And whoever relies upon Allah - then He is sufficient for him. Indeed, Allah will accomplish His purpose."* - **Quran 65:3**