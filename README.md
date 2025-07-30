# 🕌 QuranBot - Advanced Islamic Discord Bot

<div align="center">

[![CI/CD Pipeline](https://github.com/trippixn963/QuranBot/workflows/🕌%20QuranBot%20CI/CD%20Pipeline/badge.svg)](https://github.com/trippixn963/QuranBot/actions)
[![codecov](https://codecov.io/gh/trippixn963/QuranBot/branch/main/graph/badge.svg)](https://codecov.io/gh/trippixn963/QuranBot)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=trippixn963_QuranBot&metric=security_rating)](https://sonarcloud.io/dashboard?id=trippixn963_QuranBot)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=trippixn963_QuranBot&metric=alert_status)](https://sonarcloud.io/dashboard?id=trippixn963_QuranBot)

[![Python](https://img.shields.io/badge/Python-3.11+-3776ab.svg?style=flat&logo=python&logoColor=white)](https://python.org)
[![Discord.py](https://img.shields.io/badge/Discord.py-2.4+-5865f2.svg?style=flat&logo=discord&logoColor=white)](https://discordpy.readthedocs.io/)
[![License](https://img.shields.io/badge/License-MIT-00a2ed.svg?style=flat)](LICENSE)
[![Discord](https://img.shields.io/discord/YOUR_SERVER_ID?color=7289da&label=Discord&logo=discord&logoColor=white)](https://discord.gg/syria)

![GitHub Stars](https://img.shields.io/github/stars/trippixn963/QuranBot?style=social)
![GitHub Forks](https://img.shields.io/github/forks/trippixn963/QuranBot?style=social)
![GitHub Issues](https://img.shields.io/github/issues/trippixn963/QuranBot)
![GitHub Pull Requests](https://img.shields.io/github/issues-pr/trippixn963/QuranBot)

**🎯 A sophisticated 24/7 Islamic Discord bot with continuous Quran recitation, interactive learning, and comprehensive community features**

[✨ Features](#-key-features) • [📱 Screenshots](#-screenshots--demo) • [🚀 Quick Start](#-quick-start) • [📖 Documentation](#-documentation) • [🤝 Community](#-community)

</div>

![QuranBot Banner](images/BANNER%20(Still).png)

## 🌟 **What Makes QuranBot Special**

> **🤲 Interfaith Collaboration**
> Created by an Orthodox Christian developer who grew up in Syria, this project represents the beauty of interfaith friendship and collaboration. Originally built to serve a Syrian Discord community of 2,500+ members, QuranBot demonstrates how technology can bridge communities regardless of religious differences.

### **🎯 Built for Excellence (Ihsan)**
- **🔄 24/7 Continuous Operation** - Never stops serving the community
- **🎵 Professional Audio Quality** - Crystal-clear Quranic recitation
- **🧠 Advanced Learning System** - Interactive Islamic knowledge features
- **🛡️ Enterprise Security** - Production-ready with comprehensive monitoring
- **🌍 Community Driven** - Open source with active maintenance

## 📱 **Screenshots & Demo**

### **🎵 Audio Playback System**
<div align="center">
<img src="images/screenshots/Screenshot 2025-07-30 at 6.40.54 AM.png" alt="Audio Playback Interface" width="600">

*Continuous Quran recitation with real-time position tracking and beautiful Discord Rich Presence*
</div>

### **📚 Interactive Quiz System**
<div align="center">
<img src="images/screenshots/Screenshot 2025-07-30 at 6.41.06 AM.png" alt="Islamic Knowledge Quiz" width="600">

*Comprehensive Islamic knowledge quizzes with multiple categories and difficulty levels*
</div>

### **🎖️ Achievement & Progress Tracking**
<div align="center">
<img src="images/screenshots/Screenshot 2025-07-30 at 6.41.27 AM.png" alt="User Progress Dashboard" width="600">

*Detailed progress tracking with achievements, statistics, and leaderboards*
</div>

### **⚙️ Advanced Control Panel**
<div align="center">
<img src="images/screenshots/Screenshot 2025-07-30 at 6.41.41 AM.png" alt="Bot Control Panel" width="600">

*Professional control panel with comprehensive bot management and monitoring features*
</div>

## ✨ **Key Features**

### **🎵 Advanced Audio System**
- 🔄 **Continuous 24/7 Playback** - Uninterrupted Quranic recitation
- 🎭 **6+ World-Class Reciters** - Saad Al Ghamdi, Abdul Basit, Mishary Rashid, and more
- 💾 **Smart Resume Technology** - Remembers exact position across restarts
- 🎯 **Intelligent Position Tracking** - Advanced state management
- 🎨 **Rich Discord Presence** - Beautiful real-time status display

### **📚 Interactive Islamic Learning**
- 🧠 **200+ Quiz Questions** - Comprehensive Islamic knowledge across 15+ categories
- 📖 **Daily Quranic Verses** - Automated daily inspiration with translations
- 🏆 **Achievement System** - Gamified learning with progress tracking
- 📊 **Progress Analytics** - Detailed learning statistics and insights
- 🌍 **Multi-language Support** - Arabic, English, and transliterations

### **⚙️ Professional Bot Management**
- 🎛️ **Advanced Control Panel** - Professional-grade bot administration
- 📊 **Real-time Monitoring** - Comprehensive health and performance metrics
- 🔐 **Enterprise Security** - Role-based permissions and rate limiting
- 📝 **Comprehensive Logging** - Detailed audit trails and webhook integration
- 🔧 **Hot Configuration** - Live settings updates without restart

### **🏗️ Modern Architecture**
- 🏛️ **Dependency Injection** - Clean, testable, and maintainable code
- 🚀 **Microservices Design** - Scalable and resilient architecture
- 💾 **Redis Caching** - High-performance distributed caching
- 📈 **Prometheus Metrics** - Professional monitoring and observability
- 🧪 **Comprehensive Testing** - 90%+ test coverage with automated CI/CD

## 🚀 **Quick Start**

### **⚡ Option 1: Docker (Recommended)**
```bash
# 1. Clone the repository
git clone https://github.com/trippixn963/QuranBot.git
cd QuranBot

# 2. Configure your bot
cp examples/basic-setup/.env.example .env
# Edit .env with your Discord bot token and channel IDs

# 3. Launch with Docker
cd examples/basic-setup
docker-compose up -d

# 4. View logs
docker-compose logs -f quranbot
```

### **🐍 Option 2: Python Setup**
```bash
# 1. Prerequisites
python --version  # Requires Python 3.11+
ffmpeg -version   # Required for audio processing

# 2. Install dependencies
pip install poetry
poetry install

# 3. Configure environment
cp config/.env.example config/.env
# Edit with your Discord bot credentials

# 4. Run the bot
poetry run python main.py
```

### **🤖 Discord Bot Setup**
1. Create a bot at [Discord Developer Portal](https://discord.com/developers/applications)
2. Get your bot token and server/channel IDs
3. Invite bot with these permissions:
   - ✅ Send Messages
   - ✅ Use Slash Commands
   - ✅ Connect (Voice)
   - ✅ Speak (Voice)
   - ✅ Embed Links

## 📖 **Documentation**

| 📚 Guide | 📝 Description |
|----------|----------------|
| [🏗️ Installation Guide](INSTALLATION.md) | Complete setup instructions for all platforms |
| [👨‍💻 Development Guide](docs/DEVELOPMENT_GUIDE.md) | Local development and contribution setup |
| [🔧 Configuration Guide](docs/CONFIGURATION.md) | Advanced configuration and customization |
| [🏛️ Architecture Overview](docs/ARCHITECTURE.md) | Technical architecture and design patterns |
| [🛡️ Security Guide](docs/SECURITY.md) | Security best practices and guidelines |
| [📊 API Reference](docs/api/README.md) | Complete API documentation |

### **📋 Quick Links**
- **🐛 Bug Reports**: [GitHub Issues](https://github.com/trippixn963/QuranBot/issues)
- **💡 Feature Requests**: [GitHub Discussions](https://github.com/trippixn963/QuranBot/discussions)
- **❓ Get Help**: [Community Discord](https://discord.gg/syria)
- **📖 Wiki**: [Project Wiki](https://github.com/trippixn963/QuranBot/wiki)

## 🤝 **Community**

### **💬 Join Our Community**
<div align="center">

[![Discord](https://img.shields.io/badge/Discord-Join%20Server-7289da.svg?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/syria)

**[🌐 Join discord.gg/syria](https://discord.gg/syria)** - Get support, share ideas, and collaborate with the community

</div>

### **🌟 How to Contribute**
- **🐛 Report Issues**: Found a bug? Let us know!
- **💡 Suggest Features**: Have ideas? We'd love to hear them!
- **🔧 Submit PRs**: Code contributions are always welcome
- **📚 Improve Docs**: Help make our documentation better
- **⭐ Star the Repo**: Show your support!

### **🏆 Contributors**
<div align="center">

[![Contributors](https://contrib.rocks/image?repo=trippixn963/QuranBot)](https://github.com/trippixn963/QuranBot/graphs/contributors)

*Thank you to all our amazing contributors! 🙏*

</div>

## 📄 **License & Attribution**

### **📜 MIT License**
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

### **🙏 Acknowledgments**
- **Islamic Scholars** - For guidance on religious content accuracy
- **Discord Community** - For continuous feedback and support
- **Open Source Contributors** - For making this project possible
- **Syrian Friends** - For inspiring this interfaith collaboration

### **📚 Islamic Content Sources**
- **Quran Text**: Authentic sources from tanzil.net
- **Hadith References**: Sahih collections (Bukhari, Muslim, etc.)
- **Recitations**: Licensed from renowned Quranic reciters
- **Translations**: Multiple authenticated translation sources

## 🌟 **Support the Project**

<div align="center">

### **⭐ Star this repository if QuranBot helps your community!**

[![GitHub stars](https://img.shields.io/github/stars/trippixn963/QuranBot?style=social)](https://github.com/trippixn963/QuranBot/stargazers)

**Share with your community** • **Contribute code** • **Report issues** • **Join discussions**

</div>

---

<div align="center">

### **🤲 Built with Love and Interfaith Cooperation**

*"And We made them leaders guiding by Our command when they were patient and were certain of Our signs."* - **Quran 32:24**

**🕌 Serving the Islamic Community • 🤝 Bridging Communities • 💻 Built with Excellence**

[![Made with ❤️](https://img.shields.io/badge/Made%20with-❤️-red.svg)](https://github.com/trippixn963/QuranBot)
[![Built for 🕌](https://img.shields.io/badge/Built%20for-🕌%20Islamic%20Community-green.svg)](https://discord.gg/syria)

</div>
