# Contributing to QuranBot

## 🕌 Welcome to the QuranBot Community

Thank you for your interest in contributing to QuranBot! This project serves the Muslim Ummah by providing 24/7 Quran recitation and Islamic community features for Discord servers.

## 🎯 Project Mission

QuranBot aims to:
- Provide continuous Quran recitation for Islamic communities
- Offer interactive Islamic knowledge quizzes
- Foster community engagement through Islamic content
- Maintain high-quality, reliable Discord bot functionality

## 🤝 How to Contribute

### 🐛 Bug Reports

Found a bug? Help us fix it!

1. **Search existing issues** to avoid duplicates
2. **Use the bug report template** when creating new issues
3. **Provide detailed information** including:
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Python version, etc.)
   - Error logs if applicable

### ✨ Feature Requests

Have an idea for a new feature?

1. **Check existing feature requests** to avoid duplicates
2. **Use the feature request template**
3. **Consider the Islamic community impact** - how will this benefit users?
4. **Provide clear use cases** and examples

### 💻 Code Contributions

We welcome code contributions! Here's how to get started:

1. **Fork the repository** on GitHub
2. **Create a feature branch** from `master`
3. **Make your changes** following our coding standards
4. **Test thoroughly** on your local environment
5. **Submit a pull request** with a clear description

### 📚 Documentation

Help improve our documentation:

- Fix typos and grammar errors
- Add examples and tutorials
- Improve installation guides
- Create video tutorials or guides
- Translate documentation

### 🧪 Testing

Help ensure QuranBot works reliably:

- Test new features before release
- Verify bug fixes work correctly
- Test on different platforms and environments
- Provide feedback on user experience

## 🛠️ Development Setup

### Prerequisites

- Python 3.9+ (3.11 recommended)
- FFmpeg installed and accessible
- Discord bot token
- Git for version control

### Local Development

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/QuranBot.git
cd QuranBot

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up configuration
cp config/.env.example config/.env
# Edit config/.env with your bot token and settings

# Run tests
python -m pytest tests/

# Start the bot
python main.py
```

## 📋 Coding Standards

### Code Quality

- **Follow PEP 8** style guidelines
- **Use Black** for code formatting (88 character line limit)
- **Write descriptive commit messages**
- **Add comments** for complex logic
- **Include docstrings** for functions and classes

### Testing

- **Write tests** for new features
- **Ensure all tests pass** before submitting PR
- **Test with multiple Python versions** if possible
- **Test Discord interactions** manually

### Documentation

- **Update documentation** for new features
- **Add inline comments** for complex code
- **Update CHANGELOG.md** for significant changes
- **Include examples** in docstrings

## 🔍 Code Review Process

1. **Automated checks** must pass (CI/CD pipeline)
2. **Manual review** by maintainers
3. **Testing verification** on test environment
4. **Documentation review** if applicable
5. **Community feedback** consideration

## 🌍 Community Guidelines

### Islamic Values

- **Respect**: Treat all community members with respect
- **Patience**: Be patient with new contributors
- **Constructive feedback**: Provide helpful, constructive criticism
- **Community benefit**: Focus on what benefits the Muslim Ummah

### Communication

- **Be clear and concise** in issues and PRs
- **Use appropriate language** suitable for an Islamic community
- **Provide context** for your contributions
- **Be responsive** to feedback and questions

## 🎖️ Recognition

Contributors are recognized in:

- **CONTRIBUTORS.md** file
- **GitHub contributors** section
- **Release notes** for significant contributions
- **Community Discord** server (if applicable)

## 📞 Getting Help

- **GitHub Issues**: For bug reports and feature requests
- **GitHub Discussions**: For general questions and community chat
- **Discord**: Join our community server for real-time help

## 🚀 Release Process

1. **Feature development** on feature branches
2. **Testing** on development environment
3. **Code review** and approval
4. **Merge to master** branch
5. **Automated testing** via CI/CD
6. **Version tagging** and release notes
7. **Documentation updates**

## 📜 License

By contributing to QuranBot, you agree that your contributions will be licensed under the MIT License.

## 🙏 Thank You

Every contribution, no matter how small, helps make QuranBot better for the entire Muslim community. Whether you're:

- 🐛 Reporting bugs
- 💡 Suggesting features
- 💻 Writing code
- 📚 Improving documentation
- 🧪 Testing features
- 🌍 Helping other users

**You are making a difference for the Ummah!**

---

_"And whoever does righteous deeds, whether male or female, while being a believer - those will enter Paradise and will not be wronged, [even as much as] the speck on a date seed." - Quran 4:124_

_May Allah (SWT) bless your contributions to this project._
