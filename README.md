# 🕌 QuranBot - Professional Discord Audio Bot

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Discord.py](https://img.shields.io/badge/Discord.py-2.0+-blue.svg)](https://discordpy.readthedocs.io/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-4.0.1-orange.svg)](src/version.py)
[![Status](https://img.shields.io/badge/Status-ARCHIVED-red.svg)](README.md)

> **⚠️ PROJECT ARCHIVED - NO SUPPORT PROVIDED**
> 
> This project is now **ARCHIVED** and provided **AS-IS** with **NO SUPPORT, ASSISTANCE, OR MAINTENANCE**. 
> 
> - ❌ **No support requests will be answered**
> - ❌ **No issues will be addressed** 
> - ❌ **No pull requests will be accepted**
> - ❌ **No forks will be supported or assisted**
> - ❌ **No development help will be provided**
> 
> **Take it or leave it** - Use at your own risk and responsibility.

A professional Discord bot that provides **100% automated** 24/7 Quranic recitation with optional interactive features. Built with modern Python architecture featuring dependency injection, microservices, and enterprise-grade reliability.

**🤲 Created by an Orthodox Christian**
This project was created by an Orthodox Christian developer who grew up in Syria surrounded by Muslim friends and community. Now owning a Syrian Discord server with over 2,500 members, this bot was originally developed to serve that community's needs. The project represents the beauty of interfaith friendship and collaboration, where technology bridges communities regardless of religious differences.

![QuranBot Banner](<images/BANNER%20(Still).png>)

## 🚨 ARCHIVED PROJECT NOTICE

**This project has been permanently archived and is no longer maintained.**

### What This Means:
- ✅ **Code is available** - You can download and use the code
- ✅ **Documentation included** - Complete setup and deployment guides provided
- ✅ **Working codebase** - Last known working state preserved
- ❌ **Zero support** - No help, troubleshooting, or guidance provided
- ❌ **No updates** - No bug fixes, features, or security patches
- ❌ **No community** - No Discord server, forums, or communication channels

### If You Use This Code:
- You are **100% on your own**
- Read the documentation thoroughly
- Don't ask for help anywhere
- Don't expect any responses to issues
- Don't create pull requests
- Don't fork expecting support

## 🔄 Recent Project Cleanup (Final Update)

### **🎯 Final Codebase Optimization & Feature Enhancement**

- **✅ Removed Legacy Code**: Eliminated 5 duplicate/unused files (70KB saved)
- **✅ Cleaned Documentation**: Removed 5 redundant docs (64KB saved) 
- **✅ Standardized Style**: All 100+ Python files now use consistent box comments
- **✅ Updated Dependencies**: Fixed version mismatches and outdated packages
- **✅ Quiz Enhancement**: Auto-deletion after 2 minutes for questions and results
- **✅ Modern Architecture**: Complete modernization with DI container and microservices

### **🚀 Latest Major Enhancements (Final Release)**

- **✅ Enhanced Webhook System**: Multi-channel Discord webhook routing with rich visualizations
- **✅ Prometheus Metrics**: Comprehensive monitoring and metrics collection endpoints  
- **✅ Redis Caching**: Distributed caching system replacing in-memory cache
- **✅ User Analytics**: Detailed listening history and behavioral pattern analysis
- **✅ Content Expansion**: 200+ quiz questions and 60+ verses with Arabic, translations, and transliterations
- **✅ Rich Visualizations**: Progress bars, charts, and gauges in Discord embeds

### **📁 Final Project Structure**

```
QuranBot/
├── src/                    # Modern architecture source code
│   ├── analytics/         # User listening analytics and behavioral tracking
│   ├── caching/          # Redis distributed caching system
│   ├── commands/         # Discord slash commands
│   ├── config/           # Configuration management  
│   ├── core/             # Core services (DI, logging, webhook routing)
│   ├── monitoring/       # Prometheus metrics and health monitoring
│   ├── services/         # Modern services (audio, state, AI)
│   └── utils/            # Utility modules
├── data/                 # Expanded content (200+ quiz questions, 60+ verses)
├── docs/                 # Streamlined documentation (10 essential guides)
├── tests/                # Comprehensive test suite
├── tools/                # Management and deployment scripts
└── main.py               # Main entry point
```

## 🚀 What QuranBot Offers (If You Can Get It Working)

### **🎵 Advanced Audio System**

- **100% Automated Playback**: Continuous Quran recitation with zero manual intervention
- **Smart Resume**: Remembers exact position across bot restarts and crashes
- **6+ World-Class Reciters**: Saad Al Ghamdi, Abdul Basit, Maher Al Muaiqly, and more
- **Intelligent State Management**: Advanced position tracking and persistence
- **Rich Discord Presence**: Shows current Surah and playback status

### **📚 Interactive Learning Features**

- **Islamic Knowledge Quizzes**: 200+ comprehensive questions across 15 categories (Quran, Hadith, Islamic History, Law, Ethics, etc.)
- **Community Leaderboards**: Point-based ranking system with statistics
- **Daily Verses**: 60+ curated Quranic verses with Arabic text, English translations, and transliterations
- **Prayer Time Notifications**: Mecca prayer times with beautiful formatting

### **🤖 AI-Powered Islamic Assistant**

- **Enhanced AI Service**: GPT-3.5 Turbo integration for Islamic Q&A
- **Bilingual Support**: Understands Arabic input, responds in English
- **Syrian Cultural Context**: Specialized knowledge for Syrian Muslim community
- **Rate Limited**: 1 question per hour per user for quality interactions

### **🏗️ Enterprise Architecture**

- **Dependency Injection**: Modern service container with lifecycle management
- **Microservices Design**: Modular, scalable, and maintainable architecture
- **Structured Logging**: JSON-based logging with correlation IDs
- **Performance Monitoring**: Real-time metrics and system health tracking
- **Comprehensive Security**: Rate limiting, input validation, and access control

### **🔧 Advanced Monitoring & Caching**

- **Prometheus Metrics**: Comprehensive monitoring with custom metrics endpoints
- **Redis Distributed Caching**: High-performance caching replacing in-memory systems
- **User Analytics**: Detailed listening history and behavioral pattern analysis
- **Rich Webhook Visualizations**: Multi-channel Discord logging with progress bars, charts, and gauges

## 💿 Installation (No Support Provided)

### **System Requirements**
- Python 3.11+
- FFmpeg
- Discord Bot Token
- Redis Server (for distributed caching)
- 2GB+ RAM
- Ubuntu/Debian (recommended)

### **Quick Setup** (Figure It Out Yourself)
```bash
# Clone repository
git clone https://github.com/trippixn963/QuranBot.git
cd QuranBot

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt  # or use poetry

# Configure
cp config/.env.example config/.env
# Edit config/.env with your settings

# Run
python main.py
```

## 📚 Documentation (Read It Yourself)

The `docs/` folder contains comprehensive guides:

- **[Development Guide](docs/DEVELOPMENT_GUIDE.md)**: Local setup and development
- **[Deployment Guide](docs/DEPLOYMENT_GUIDE.md)**: Production deployment
- **[Architecture](docs/ARCHITECTURE.md)**: System design and components
- **[API Reference](docs/API_REFERENCE.md)**: Service documentation
- **[Troubleshooting](docs/TROUBLESHOOTING.md)**: Common issues (solve them yourself)
- **[Security](docs/SECURITY.md)**: Security best practices
- **[VPS Management](docs/VPS_MANAGEMENT.md)**: Server administration

## ⚠️ Disclaimers

### **No Support Policy**
- This is an **AS-IS** release with **ZERO** ongoing support
- Don't ask questions, report bugs, or request features
- Don't expect help with setup, configuration, or deployment
- Don't create GitHub issues or discussions
- Don't fork expecting any assistance or guidance

### **Technical Warnings**
- Complex architecture requiring advanced Python knowledge
- Requires proper Discord bot setup and permissions
- May have undiscovered bugs or compatibility issues
- Dependencies may become outdated over time
- No guarantee of continued functionality

### **Islamic Content Disclaimer**
- Islamic content provided for educational purposes
- Verify religious accuracy with qualified Islamic scholars
- Creator is not responsible for religious interpretation
- Use Islamic features with appropriate respect and understanding

## 📜 License & Credits

### **MIT License**
This project is released under the MIT License. See [LICENSE](LICENSE) for details.

### **No Warranty**
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.

### **Final Acknowledgments**
- **Allah (SWT)** for enabling this project's creation
- **Syrian Muslim community** for inspiration and feedback  
- **Islamic scholars** who provided religious guidance
- **Open source community** for tools and libraries used
- **Discord.py developers** for the excellent framework

---

## 🏁 Final Words

This project served the Muslim community for its intended purpose and is now complete. The code is preserved here as a final contribution to the open source community.

**Take what you can use, ignore what you can't.**

**No further communication will be provided regarding this project.**

_"And Allah knows best."_

**الحمد لله رب العالمين**
