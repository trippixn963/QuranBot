# 🕌 QuranBot - Advanced Islamic Discord Bot

<div align="center">

[![GitHub release](https://img.shields.io/github/v/release/trippixn963/QuranBot?style=flat&color=00D4AA)](https://github.com/trippixn963/QuranBot/releases)
[![Python](https://img.shields.io/badge/Python-3.11+-3776ab.svg?style=flat&logo=python&logoColor=white)](https://python.org)
[![Discord.py](https://img.shields.io/badge/Discord.py-2.4+-5865f2.svg?style=flat&logo=discord&logoColor=white)](https://discordpy.readthedocs.io/)
[![License](https://img.shields.io/badge/License-MIT-00a2ed.svg?style=flat)](LICENSE)

![GitHub Stars](https://img.shields.io/github/stars/trippixn963/QuranBot?style=social)
![GitHub Forks](https://img.shields.io/github/forks/trippixn963/QuranBot?style=social)
![GitHub Issues](https://img.shields.io/github/issues/trippixn963/QuranBot)
![GitHub Last Commit](https://img.shields.io/github/last-commit/trippixn963/QuranBot)

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
- 💾 **SQLite Database** - Reliable data persistence with backup systems
- 📈 **Performance Monitoring** - Built-in metrics and health checks
- 🧪 **Comprehensive Testing** - Extensive test coverage with automated CI/CD

## 🚀 **Quick Start**

### **📋 Prerequisites**
- **Python 3.11+** (Check with `python --version`)
- **FFmpeg** (Required for audio processing)
- **Discord Bot Token** ([Get one here](https://discord.com/developers/applications))
- **4GB+ RAM** (Recommended for smooth operation)

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
# 1. Install dependencies
pip install poetry
poetry install

# 2. Configure environment
cp config/.env.example .env
# Edit .env with your Discord bot credentials

# 3. Run the bot
poetry run python main.py
```

### **🤖 Discord Bot Setup**
1. **Create Bot**: Visit [Discord Developer Portal](https://discord.com/developers/applications)
2. **Get Token**: Copy your bot token from the "Bot" section
3. **Invite Bot**: Use these required permissions:
   - ✅ Send Messages & Embed Links
   - ✅ Use Slash Commands  
   - ✅ Connect & Speak (Voice channels)
   - ✅ Read Message History
4. **Get IDs**: Copy your server ID and channel IDs
5. **Configure**: Add all credentials to your `.env` file

### **⚙️ Basic Configuration**
```env
# Discord Bot Settings
BOT_TOKEN=your_bot_token_here
GUILD_ID=your_server_id
DAILY_VERSE_CHANNEL_ID=your_channel_id
DEVELOPER_ID=your_user_id

# Audio Settings  
DEFAULT_RECITER=Saad Al Ghamdi
DEFAULT_VOLUME=0.5
AUTO_RESUME=true

# Optional: Webhook Logging
WEBHOOK_URL=your_webhook_url_for_logging
```

## 📖 **Documentation**

### **📚 Complete Guides**
| 📗 Guide | 📝 Description |
|----------|----------------|
| [🏗️ Installation Guide](INSTALLATION.md) | Complete setup instructions for all platforms |
| [👨‍💻 Development Guide](docs/DEVELOPMENT_GUIDE.md) | Local development and contribution setup |
| [🔧 Configuration Guide](CONFIG_MIGRATION.md) | Advanced configuration and customization |
| [🏛️ Architecture Overview](docs/ARCHITECTURE.md) | Technical architecture and design patterns |
| [🛡️ Security Guide](docs/SECURITY.md) | Security best practices and guidelines |
| [📊 API Reference](docs/api/README.md) | Complete API documentation |

### **🔧 Troubleshooting**
**Common Issues:**
- **Bot not responding**: Check bot permissions and token
- **Audio not playing**: Verify FFmpeg installation and voice permissions  
- **Commands not working**: Ensure slash commands are synced (`/sync` command)
- **Memory issues**: Monitor with `/health` command
- **Configuration errors**: Validate with `python scripts/validate_config.py`

**Get Help:**
- 📋 **Check Logs**: Use `docker-compose logs` or check `logs/` directory
- 🐛 **Report Issues**: [GitHub Issues](https://github.com/trippixn963/QuranBot/issues)
- 💬 **Community Support**: [Discord Server](https://discord.gg/syria)
- 📖 **Documentation**: [Full Documentation](docs/)

## 🤝 **Community**

### **💬 Join Our Community**
<div align="center">

[![Discord](https://img.shields.io/badge/Discord-Join%20Server-7289da.svg?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/syria)

**[🌐 Join discord.gg/syria](https://discord.gg/syria)** - Get support, share ideas, and collaborate with the community

</div>

### **🌟 How to Contribute**
We welcome all contributions! Here's how you can help:

- **🐛 Report Bugs**: [Create an issue](https://github.com/trippixn963/QuranBot/issues/new?template=bug_report.md)
- **💡 Request Features**: [Start a discussion](https://github.com/trippixn963/QuranBot/discussions)
- **🔧 Submit Code**: [Fork and create a PR](https://github.com/trippixn963/QuranBot/fork)
- **📚 Improve Docs**: Help make our documentation clearer
- **⭐ Star the Repo**: Show your support and help others discover the project

### **🏆 Contributors**
<div align="center">

[![Contributors](https://contrib.rocks/image?repo=trippixn963/QuranBot)](https://github.com/trippixn963/QuranBot/graphs/contributors)

*Thank you to all our amazing contributors! 🙏*

</div>

## 📊 **Project Stats**

<div align="center">

![GitHub Language Count](https://img.shields.io/github/languages/count/trippixn963/QuranBot)
![GitHub Top Language](https://img.shields.io/github/languages/top/trippixn963/QuranBot)
![GitHub Code Size](https://img.shields.io/github/languages/code-size/trippixn963/QuranBot)
![GitHub Repo Size](https://img.shields.io/github/repo-size/trippixn963/QuranBot)

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

**[⭐ Star](https://github.com/trippixn963/QuranBot/stargazers)** • **[🍴 Fork](https://github.com/trippixn963/QuranBot/fork)** • **[📢 Share](https://twitter.com/intent/tweet?text=Check%20out%20QuranBot%20-%20an%20amazing%20Islamic%20Discord%20bot!&url=https://github.com/trippixn963/QuranBot)**

</div>

---

<div align="center">

### **🤲 Built with Love and Interfaith Cooperation**

*"And We made them leaders guiding by Our command when they were patient and were certain of Our signs."* - **Quran 32:24**

**🕌 Serving the Islamic Community • 🤝 Bridging Communities • 💻 Built with Excellence**

[![Made with ❤️](https://img.shields.io/badge/Made%20with-❤️-red.svg)](https://github.com/trippixn963/QuranBot)
[![Built for 🕌](https://img.shields.io/badge/Built%20for-🕌%20Islamic%20Community-green.svg)](https://discord.gg/syria)

</div>