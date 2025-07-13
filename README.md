# 🕌 QuranBot - Professional Discord Bot

*"And We have certainly made the Quran easy for remembrance, so is there any who will remember?"* - **Quran 54:17**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Discord.py](https://img.shields.io/badge/Discord.py-2.0+-blue.svg)](https://discordpy.readthedocs.io/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-3.5.1-orange.svg)](src/version.py)

A professional Discord bot that provides 24/7 Quranic recitation, interactive quizzes, daily verses, and comprehensive management tools. Built with modern Python and featuring a beautiful web dashboard for monitoring and control.

## 🌟 Key Features

### 🎵 **Audio Playback System**
- **24/7 Continuous Recitation**: Uninterrupted Quranic audio playback
- **Multiple Reciters**: Choose from 6+ world-renowned reciters
- **Smart Resume**: Automatically resumes from last position after restarts
- **Advanced Controls**: Play, pause, skip, jump to specific Surahs
- **Rich Presence**: Real-time Discord status with current Surah and elapsed time

### 🎯 **Interactive Quiz System**
- **Daily Quizzes**: Automated quiz delivery with beautiful formatting
- **Smart Scoring**: Comprehensive scoring system with leaderboards
- **User Statistics**: Track performance, accuracy, and participation
- **Customizable**: Configurable intervals and question types

### 📖 **Daily Verses**
- **Automated Delivery**: Daily verse sharing with translations
- **Beautiful Formatting**: Rich embeds with Islamic styling
- **Multiple Languages**: Support for various translations

### 🌐 **Professional Web Dashboard**
- **Real-time Monitoring**: Live bot status, audio playback, and system metrics
- **Interactive Controls**: Start, stop, pause, and control audio remotely
- **Advanced Analytics**: Quiz statistics, listening trends, and user engagement
- **System Health**: Discord API monitoring, resource usage, and performance metrics
- **Beautiful UI**: Modern, responsive design with Islamic theming

### 🛠️ **Management Tools**
- **Automated Deployment**: One-click VPS deployment with systemd services
- **Log Syncing**: Real-time log synchronization from VPS to local machine
- **Backup System**: Automated data backups with integrity verification
- **Health Monitoring**: Comprehensive system health checks and alerts

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Discord Bot Token
- FFmpeg (for audio playback)
- VPS or dedicated server (recommended for 24/7 operation)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/trippixn963/QuranBot.git
   cd QuranBot
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp config/.env.example config/.env
   # Edit config/.env with your Discord bot token and settings
   ```

5. **Run the bot**
   ```bash
   python main.py
   ```

## 🌐 Web Dashboard

QuranBot features a professional web dashboard for monitoring and control:

### **Dashboard URL**: `http://your-vps-ip:8080`

### **Features**:
- 📊 **Real-time Bot Status**: Online status, uptime, memory usage
- 🎵 **Audio Controls**: Play, pause, skip, volume control
- 📈 **Live Statistics**: Quiz performance, listening time, user engagement
- 🔍 **System Monitoring**: CPU, memory, disk usage, Discord API health
- 📋 **Log Viewer**: Real-time log streaming with search and filtering
- 👥 **User Analytics**: Leaderboards, activity tracking, engagement metrics

### **Dashboard Screenshots**:
- Beautiful Islamic-themed design with animated backgrounds
- Real-time updates every 5 seconds
- Responsive layout that works on all devices
- Interactive charts and progress bars

## 🏗️ Architecture

### **Production Setup**
```
┌─────────────────┐    📡 API Calls     ┌─────────────────┐
│   Discord API   │ ◄─────────────────► │   VPS Server    │
│                 │                     │                 │
│ • Voice Gateway │                     │ • QuranBot      │
│ • Bot Commands  │                     │ • Web Dashboard │
│ • Rich Presence │                     │ • Log System    │
└─────────────────┘                     └─────────────────┘
                                                │
                                        ┌─────────────────┐
                                        │ Local Machine   │
                                        │                 │
                                        │ • Development   │
                                        │ • Log Syncing   │
                                        │ • Monitoring    │
                                        └─────────────────┘
```

### **Core Components**
- **Bot Core** (`src/bot/main.py`): Main Discord bot logic
- **Audio Manager** (`src/utils/audio_manager.py`): Audio playback system
- **Quiz System** (`src/commands/question.py`): Interactive quiz functionality
- **Web Dashboard** (`web/app.py`): Professional monitoring interface
- **State Management** (`src/utils/state_manager.py`): Persistent data storage

## 🎛️ Configuration

### **Environment Variables**
```bash
# Discord Configuration
DISCORD_TOKEN=your_bot_token_here
GUILD_ID=your_server_id
TARGET_CHANNEL_ID=voice_channel_id
PANEL_CHANNEL_ID=control_panel_channel_id

# Audio Settings
DEFAULT_RECITER=Saad Al Ghamdi
FFMPEG_PATH=/usr/bin/ffmpeg
AUDIO_QUALITY=128k

# VPS Configuration
VPS_HOST=root@your-vps-ip
DASHBOARD_URL=http://your-vps-ip:8080
```

### **Available Reciters**
- Saad Al Ghamdi
- Abdul Basit Abdul Samad
- Maher Al Muaiqly
- Muhammad Al Luhaidan
- Mishary Rashid Alafasy
- And more...

## 📊 Management Commands

### **VPS Management**
```bash
# Quick status check
qb-status && qb-audio && qb-daemon-status

# Bot control
qb-restart     # Restart bot
qb-logs        # View live logs
qb-system      # System information

# Log syncing
qb-sync        # One-time sync
qb-sync-daemon # Continuous sync
```

### **Development Tools**
```bash
# Testing
python tools/test_bot.py

# Version management
python tools/update_version.py

# Deployment
python tools/deploy.py
```

## 🛡️ Security & Best Practices

### **Production Deployment**
- Uses systemd services for 24/7 operation
- Automatic restart on failure
- Resource monitoring and limits
- Secure SSH key-based authentication
- Environment variable protection

### **Data Protection**
- Automated backups with integrity checks
- Encrypted data transmission
- User privacy protection
- GDPR compliance considerations

## 📈 Monitoring & Analytics

### **System Health**
- Real-time performance metrics
- Discord API health monitoring
- Audio playback status tracking
- Resource usage alerts

### **User Analytics**
- Quiz participation statistics
- Listening time tracking
- Engagement metrics
- Leaderboard systems

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Quran.com** for audio resources
- **Discord.py** community for excellent documentation
- **Islamic community** for inspiration and support
- **Open source contributors** for their valuable contributions

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/trippixn963/QuranBot/issues)
- **Documentation**: [Wiki](https://github.com/trippixn963/QuranBot/wiki)
- **Discord**: Join our support server

---

*"And whoever relies upon Allah - then He is sufficient for him. Indeed, Allah will accomplish His purpose."* - **Quran 65:3**

## 🔄 Recent Updates (v3.5.1)

### **Rich Presence Fixes**
- ✅ Fixed rich presence elapsed time display (no longer stuck at 00:00)
- ✅ Implemented Discord's automatic elapsed time tracking
- ✅ Added proper start_time handling for resume functionality
- ✅ Updated rich presence templates for better display

### **Web Dashboard Enhancements**
- ✅ Professional web interface with Islamic theming
- ✅ Real-time monitoring and control capabilities
- ✅ Advanced analytics and user statistics
- ✅ Responsive design with animated backgrounds

### **System Improvements**
- ✅ Enhanced log sync manager with VPS detection
- ✅ Improved error handling and recovery
- ✅ Better resource monitoring and optimization
- ✅ Automated deployment scripts

---

**Built with ❤️ for the Islamic community** 