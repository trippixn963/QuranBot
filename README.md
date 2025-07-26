# 🕌 QuranBot - Professional Discord Bot (Modernized Architecture)

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Discord.py](https://img.shields.io/badge/Discord.py-2.0+-blue.svg)](https://discordpy.readthedocs.io/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-4.0.1-orange.svg)](src/version.py)

A professional Discord bot that provides **100% automated** 24/7 Quranic recitation with optional interactive features. Built with modern Python architecture featuring dependency injection, microservices, and enterprise-grade reliability.

**🤲 Created by an Orthodox Christian**
This project was created by an Orthodox Christian developer (ME) who grew up in Syria surrounded by Muslim friends and community. Now owning a Syrian Discord server with over 2,500 members, this bot was originally developed to serve that community's needs. The project represents the beauty of interfaith friendship and collaboration, where technology bridges communities regardless of religious differences.

![QuranBot Banner](<images/BANNER%20(Still).png>)

## 🚀 Latest Updates (v4.0.1)

### ✅ **Recently Fixed & Enhanced**

- **🔧 Quiz System Restoration**: Fully restored `/question` command functionality from stable GitHub version
- **📩 Admin DM Integration**: Automatic quiz answer delivery with rich embeds and direct message links
- **🖼️ Enhanced Quiz Results**: Admin profile pictures now display in quiz result footers
- **⚡ Signal Handling**: Fixed Ctrl+C graceful shutdown functionality
- **🏗️ Dependency Resolution**: Resolved configuration service integration issues
- **🎯 Command Loading**: Fixed QuizView constructor and method naming inconsistencies
- **📱 Error Handling**: Improved error messages and fallback behavior

### 🔄 **Modernization Complete**

- **✅ All legacy issues resolved**: Bot now runs without errors or exceptions
- **✅ Command system stable**: All slash commands working perfectly
- **✅ Audio system optimized**: Seamless playback with smart resume functionality
- **✅ Configuration unified**: Single source of truth for all settings
- **✅ Testing comprehensive**: All components verified and operational

## 🌟 Key Features

### 🎵 **100% Automated Audio System**

- **Zero Manual Intervention**: Fully automated 24/7 continuous recitation
- **Smart Auto-Start**: Automatically begins recitation on bot startup
- **Intelligent Resume**: Seamlessly resumes from exact position after any interruption
- **Multiple Reciters**: Choose from 6+ world-renowned reciters
- **Advanced Audio Service**: Enterprise-grade audio processing with modern architecture
- **Rich Presence Integration**: Real-time Discord status with current Surah and elapsed time

### 🏗️ **Modern Architecture**

- **Dependency Injection**: Clean, testable, and maintainable code structure
- **Microservices Design**: Modular services for audio, state, caching, and more
- **Performance Monitoring**: Real-time performance metrics and system health
- **Resource Management**: Intelligent resource allocation and cleanup
- **Security Service**: Built-in rate limiting and security features
- **Structured Logging**: Comprehensive logging with modern structured format

### 🎯 **Interactive Features (Optional)**

- **Daily Quizzes**: Automated quiz delivery with beautiful formatting
- **Smart Scoring**: Comprehensive scoring system with leaderboards
- **User Statistics**: Track performance, accuracy, and participation
- **Slash Commands**: Modern Discord slash command integration
- **Admin DM Integration**: Automatic answer delivery to administrators
- **Enhanced Quiz Results**: Profile picture integration in quiz footers

### 📖 **Daily Verses**

- **Automated Delivery**: Daily verse sharing with translations
- **Beautiful Formatting**: Rich embeds with Islamic styling
- **Multiple Languages**: Support for various translations

### 🔧 **Enterprise Management**

- **Modern Service Architecture**: Clean separation of concerns
- **Advanced Caching**: Multi-strategy caching with persistence
- **State Persistence**: Reliable state management with automatic backup
- **Health Monitoring**: Comprehensive system health checks
- **Professional Deployment**: Streamlined VPS deployment with systemd services

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
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

3. **Install Poetry (if not already installed)**

   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

4. **Install dependencies**

   ```bash
   poetry install
   ```

5. **Configure environment**

   ```bash
   cp config/.env.example config/.env
   # Edit config/.env with your Discord bot token and settings
   ```

6. **Run the modernized bot**

   ```bash
   # For development with full features
   python main.py

   # For modernized architecture (recommended)
   python main_modernized.py
   ```

## 🏗️ Modernized Architecture

### **Service Architecture**

```
┌─────────────────────────────────────────────────────────────┐
│                     Discord Bot Core                        │
├─────────────────────────────────────────────────────────────┤
│                 Dependency Injection Container              │
├─────────────────┬─────────────────┬─────────────────────────┤
│   Core Services │  Modern Services│    Utility Services     │
├─────────────────┼─────────────────┼─────────────────────────┤
│ • CacheService  │ • AudioService  │ • RichPresenceManager   │
│ • PerformanceM. │ • StateService  │ • ControlPanel          │
│ • ResourceMgr   │ • MetadataCache │ • QuizManager           │
│ • SecuritySvc   │ • ConfigService │ • DailyVerses           │
│ • StructuredLog │                 │ • BackupManager         │
└─────────────────┴─────────────────┴─────────────────────────┘
```

### **Dependency Injection Architecture**

The modernized QuranBot uses a comprehensive dependency injection system that manages all services:

- **DIContainer**: Central service registry and resolver
- **Service Lifecycle**: Automatic initialization and cleanup
- **Configuration Management**: Type-safe configuration with validation
- **Error Handling**: Structured error handling with custom exceptions
- **Performance Monitoring**: Built-in metrics and profiling
- **Security**: Rate limiting and input validation

### **Production Deployment**

```
┌─────────────────┐    📡 API Calls     ┌─────────────────┐
│   Discord API   │ ◄─────────────────► │   VPS Server    │
│                 │                     │                 │
│ • Voice Gateway │                     │ • QuranBot      │
│ • Bot Commands  │                     │ • Audio Service │
│ • Rich Presence │                     │ • State Service │
│ • Webhooks      │                     │ • Cache Service │
└─────────────────┘                     └─────────────────┘
                                                │
                                        ┌─────────────────┐
                                        │ Local Machine   │
                                        │                 │
                                        │ • Development   │
                                        │ • Log Syncing   │
                                        │ • Code Updates  │
                                        └─────────────────┘
```

### **Core Components**

#### **Modern Services** (`src/services/`)

- **AudioService**: Enterprise-grade audio processing with dependency injection
- **StateService**: Advanced state management with backup and validation
- **MetadataCache**: Intelligent metadata caching for audio files
- **ConfigService**: Type-safe configuration management with validation

#### **Core Infrastructure** (`src/core/`)

- **DIContainer**: Dependency injection container for clean architecture
- **StructuredLogger**: Modern structured logging with JSON output and correlation IDs
- **CacheService**: Multi-strategy caching (LRU, TTL, LFU) with persistence
- **PerformanceMonitor**: Real-time performance metrics and profiling
- **ResourceManager**: Intelligent resource allocation and cleanup
- **SecurityService**: Rate limiting, input validation, and security features
- **Custom Exceptions**: Hierarchical exception system with context

#### **Data Models** (`src/data/`)

- **Pydantic Models**: Type-safe data validation for all system state
- **PlaybackState**: Validated audio playback state management
- **QuizStatistics**: User quiz performance tracking
- **Configuration Models**: Structured configuration with validation

#### **Utility Services** (`src/utils/`)

- **Control Panel**: Interactive Discord control interface
- **Rich Presence Manager**: Intelligent Discord status management
- **Quiz Manager**: Advanced quiz system with scoring
- **Daily Verses**: Automated verse delivery system
- **Tree Logger**: Beautiful console logging for development

## 🎛️ Configuration

### **Environment Variables**

```bash
# Environment
ENVIRONMENT=production

# Discord Configuration
DISCORD_TOKEN=your_bot_token_here
GUILD_ID=your_server_id

# Discord Users & Permissions
ADMIN_USER_ID=your_user_id
DEVELOPER_ID=your_user_id
PANEL_ACCESS_ROLE_ID=panel_role_id

# Discord Channel IDs
TARGET_CHANNEL_ID=voice_channel_id
PANEL_CHANNEL_ID=control_panel_channel_id
LOGS_CHANNEL_ID=log_channel_id
DAILY_VERSE_CHANNEL_ID=verse_channel_id

# Audio Configuration
AUDIO_FOLDER=audio
DEFAULT_RECITER=Saad Al Ghamdi
AUDIO_QUALITY=128k
DEFAULT_SHUFFLE=false
DEFAULT_LOOP=false
FFMPEG_PATH=/usr/bin/ffmpeg

# Performance Configuration
CACHE_TTL=300
MAX_CONCURRENT_AUDIO=1
BACKUP_INTERVAL_HOURS=24

# Security Configuration
RATE_LIMIT_PER_MINUTE=10

# Logging Configuration
LOG_LEVEL=INFO
USE_WEBHOOK_LOGGING=true
DISCORD_WEBHOOK_URL=your_webhook_url

# VPS Configuration
VPS_HOST=root@your-vps-ip
```

### **Available Reciters**

- Saad Al Ghamdi (Default)
- Abdul Basit Abdul Samad
- Maher Al Muaiqly
- Muhammad Al Luhaidan
- Mishary Rashid Alafasy
- And more...

## 📊 Monitoring & Management

### **System Monitoring**:

- 📊 **Performance Metrics**: Real-time CPU, memory, and resource monitoring
- 🎵 **Audio State Tracking**: Detailed audio service state management
- 📈 **Cache Analytics**: Cache hit rates, performance, and optimization
- 🔍 **Health Checks**: Automated system health monitoring and alerts
- 📋 **Structured Logging**: JSON-based logging with detailed error tracking
- 👥 **User Analytics**: Comprehensive user engagement and activity metrics

### **VPS Management**

```bash
# Quick status check
qb-status && qb-audio && qb-daemon-status

# Bot control
qb-restart     # Restart bot service
qb-logs        # View live logs
qb-system      # System information

# Log syncing
qb-sync        # One-time sync
qb-sync-daemon # Continuous sync
```

## 🛡️ Security & Best Practices

### **Modern Security Features**

- **Rate Limiting**: Built-in rate limiting service
- **Input Validation**: Comprehensive input validation and sanitization
- **Resource Protection**: Memory and CPU usage monitoring
- **Secure Configuration**: Environment-based configuration management

### **Production Deployment**

- **Systemd Services**: Professional service management for 24/7 operation
- **Automatic Restart**: Intelligent restart on failure with exponential backoff
- **Resource Monitoring**: Memory and CPU limits with alerting
- **SSH Security**: Key-based authentication and secure deployment
- **Environment Protection**: Secure environment variable handling

### **Data Protection**

- **Automated Backups**: Scheduled backups with integrity verification
- **State Persistence**: Reliable state management across restarts
- **Encrypted Communication**: Secure Discord API communication
- **Privacy Protection**: User data protection and GDPR compliance

## 🚀 Deployment Guide

### **Development Setup**

```bash
# Clone and setup
git clone https://github.com/trippixn963/QuranBot.git
cd QuranBot
python -m venv .venv
source .venv/bin/activate
poetry install

# Configure
cp config/.env.example config/.env
# Edit config/.env with your settings

# Run development version
python main_modernized.py
```

### **Production Deployment**

```bash
# VPS deployment (Ubuntu/Debian)
ssh root@your-vps-ip

# Create project directory
mkdir -p /opt/QuranBot
cd /opt/QuranBot

# Clone repository
git clone https://github.com/trippixn963/QuranBot.git .

# Setup Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install poetry
poetry install --only=main

# Configure environment
cp config/.env.example config/.env
# Edit config/.env for production

# Create systemd service
sudo cp deploy/quranbot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable quranbot
sudo systemctl start quranbot

# Check status
sudo systemctl status quranbot
```

## 📚 Documentation

- **[Architecture Guide](docs/ARCHITECTURE.md)**: Detailed architecture documentation
- **[Development Guide](docs/DEVELOPMENT_GUIDE.md)**: Development setup and guidelines
- **[Deployment Guide](docs/DEPLOYMENT_GUIDE.md)**: Production deployment instructions
- **[Troubleshooting Guide](docs/TROUBLESHOOTING.md)**: Common issues and solutions
- **[API Reference](docs/API_REFERENCE.md)**: Service and API documentation

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Follow the development guidelines in `docs/DEVELOPMENT_GUIDE.md`
4. Commit your changes (`git commit -m 'Add amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Quran.com** for audio resources
- **Discord.py** community for excellent documentation
- **Islamic community** for inspiration and support
- **Open source contributors** for their valuable contributions

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/trippixn963/QuranBot/issues)
- **Documentation**: [docs/](docs/)
- **Discord**: Join our support server

---

_"And whoever relies upon Allah - then He is sufficient for him. Indeed, Allah will accomplish His purpose."_ - **Quran 65:3**

## 🔄 Recent Updates (v4.0.0 - Modernized)

### **🏗️ Complete Architecture Modernization**

- ✅ **Dependency Injection**: Implemented enterprise-grade DI container
- ✅ **Microservices Architecture**: Modular service-based design
- ✅ **100% Automation**: Zero manual intervention for audio playback
- ✅ **Modern Services**: AudioService, StateService, CacheService, and more

### **🎵 Enhanced Audio System**

- ✅ **Automated Startup**: Bot automatically starts recitation on connection
- ✅ **Intelligent Resume**: Seamless position tracking and resume functionality
- ✅ **Advanced Processing**: Enterprise-grade audio processing pipeline
- ✅ **Rich Integration**: Real-time Discord presence updates

### **⚡ Performance & Reliability**

- ✅ **Performance Monitoring**: Real-time metrics and profiling
- ✅ **Resource Management**: Intelligent memory and CPU management
- ✅ **Advanced Caching**: Multi-strategy caching with persistence
- ✅ **Structured Logging**: JSON-based logging with detailed tracking

### **🛡️ Security & Management**

- ✅ **Security Service**: Built-in rate limiting and protection
- ✅ **Health Monitoring**: Comprehensive system health checks
- ✅ **Professional Deployment**: Streamlined production deployment
- ✅ **Modern Configuration**: Environment-based configuration management

---

**Built with ❤️ for the Islamic community using modern enterprise architecture**
