# 🛠️ QuranBot Development Guide

*"And Allah has extracted you from the wombs of your mothers not knowing a thing, and He made for you hearing and vision and intellect that perhaps you would be grateful."* - **Quran 16:78**

## Overview

This guide provides comprehensive instructions for developers who want to contribute to QuranBot, set up a development environment, understand the codebase architecture, and follow best practices for Islamic software development.

---

## 📋 Development Prerequisites

### Required Software
- **Python 3.9+** (recommended 3.11+)
- **Git** for version control
- **Discord Developer Account** for bot testing
- **FFmpeg** for audio processing
- **Code Editor** (VS Code, PyCharm, or Cursor recommended)

### Optional Tools
- **Docker** for containerized development
- **pytest** for testing
- **black** for code formatting
- **mypy** for type checking

---

## 🏗️ Development Environment Setup

### 1. Fork and Clone Repository

```bash
# Fork the repository on GitHub first, then:
git clone https://github.com/yourusername/QuranBot.git
cd QuranBot

# Add upstream remote
git remote add upstream https://github.com/originalowner/QuranBot.git
```

### 2. Virtual Environment Setup

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
# .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest black mypy flake8
```

### 3. Configuration Setup

```bash
# Copy environment template
cp config/.env.example config/.env

# Edit configuration for development
nano config/.env
```

**Development Configuration Example:**
```bash
# Discord Bot Configuration
DISCORD_TOKEN=your_development_bot_token
GUILD_ID=your_test_server_id
TARGET_CHANNEL_ID=your_test_voice_channel_id
PANEL_CHANNEL_ID=your_test_text_channel_id
DEVELOPER_ID=your_discord_user_id

# Development Settings
FFMPEG_PATH=/opt/homebrew/bin/ffmpeg  # macOS
# FFMPEG_PATH=/usr/bin/ffmpeg         # Linux
DEFAULT_RECITER=Saad Al Ghamdi
DEFAULT_SHUFFLE=false
DEFAULT_LOOP=false

# Optional Development Settings
LOGS_CHANNEL_ID=0  # Disable for local development
DAILY_VERSE_CHANNEL_ID=0
```

### 4. Audio Files Setup

```bash
# Create audio directory structure
mkdir -p audio/Saad\ Al\ Ghamdi

# For development, you can use sample files or download full recitations
# Structure should be: audio/Reciter Name/001.mp3, 002.mp3, etc.
```

---

## 🏛️ Project Architecture

### Directory Structure

```
QuranBot/
├── src/                    # Core bot functionality
│   ├── bot/               # Main bot initialization
│   │   ├── __init__.py
│   │   └── main.py        # Bot entry point
│   ├── commands/          # Discord slash commands
│   │   ├── credits.py     # Bot information
│   │   ├── interval.py    # Interval management
│   │   ├── leaderboard.py # Quiz leaderboard
│   │   ├── question.py    # Quiz system
│   │   └── verse.py       # Verse playback
│   └── utils/             # Utility modules
│       ├── audio_manager.py    # Audio playback
│       ├── backup_manager.py   # Data backup
│       ├── control_panel.py    # Discord UI
│       ├── daily_verses.py     # Verse scheduling
│       ├── discord_logger.py   # Discord logging
│       ├── listening_stats.py  # User statistics
│       ├── quiz_manager.py     # Quiz logic
│       ├── rich_presence.py    # Discord status
│       ├── state_manager.py    # Data persistence
│       ├── surah_mapper.py     # Quran data
│       └── tree_log.py         # Logging system
├── config/                # Configuration files
├── tests/                 # Test suite
├── tools/                 # Development utilities
├── vps/                   # VPS deployment
├── docs/                  # Documentation
├── audio/                 # Quranic recitations
├── data/                  # Runtime data
├── logs/                  # Application logs
└── backup/                # Automatic backups
```

### Core Components

#### 1. Bot Core (`src/bot/main.py`)
- Discord bot initialization
- Event handlers
- Command registration
- Global error handling

#### 2. Audio System (`src/utils/audio_manager.py`)
- Multi-reciter audio playback
- Position tracking and resume
- Loop and shuffle modes
- Voice channel management

#### 3. Quiz System (`src/utils/quiz_manager.py`)
- Islamic knowledge questions
- Leaderboard tracking
- User statistics
- Automated scheduling

#### 4. State Management (`src/utils/state_manager.py`)
- Data persistence
- Backup creation
- Recovery mechanisms
- Session tracking

#### 5. Control Panel (`src/utils/control_panel.py`)
- Discord UI components
- Interactive buttons and selects
- Real-time updates
- User-friendly controls

---

## 🔧 Development Workflow

### 1. Feature Development Process

```bash
# 1. Create feature branch
git checkout -b feature/new-islamic-feature

# 2. Develop and test
# ... make your changes ...

# 3. Run tests
python -m pytest tests/

# 4. Format code
black src/ tests/

# 5. Type checking
mypy src/

# 6. Commit changes
git add .
git commit -m "feat: add new Islamic feature for community benefit"

# 7. Push and create PR
git push origin feature/new-islamic-feature
```

### 2. Code Style Guidelines

#### Python Style
- Follow **PEP 8** standards
- Use **type hints** for all functions
- Write **docstrings** for all classes and functions
- Prefer **descriptive variable names**

#### Islamic Considerations
- Use respectful language in comments and documentation
- Include Islamic context in feature descriptions
- Add Quranic verses or Hadith references where appropriate
- Consider Islamic values in feature design

#### Example Code Style:
```python
from typing import Optional, Dict, Any
import asyncio

class IslamicFeature:
    """
    Islamic feature implementation following Quran and Sunnah principles.
    
    This class provides functionality for the Muslim community while
    maintaining respect for Islamic values and teachings.
    """
    
    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize Islamic feature with configuration."""
        self.config = config
        self.is_active = False
    
    async def serve_community(self, user_id: int) -> Optional[str]:
        """
        Serve the Muslim community with this feature.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Success message or None if failed
            
        Note:
            This function embodies the Islamic principle of serving others.
            "And whoever saves a life, it is as if he has saved all mankind" - Quran 5:32
        """
        try:
            # Implementation here
            return "Feature served successfully, barakAllahu feek"
        except Exception as e:
            # Handle gracefully
            return None
```

### 3. Testing Guidelines

#### Test Structure
```bash
tests/
├── test_audio_manager.py      # Audio system tests
├── test_quiz_manager.py       # Quiz system tests
├── test_state_manager.py      # State management tests
├── test_control_panel.py      # UI component tests
├── test_daily_verses.py       # Verse scheduling tests
├── test_listening_stats.py    # Statistics tests
├── test_rich_presence.py      # Discord status tests
├── test_surah_mapper.py       # Quran data tests
├── test_tree_log.py           # Logging tests
└── test_utils.py              # Utility tests
```

#### Writing Tests
```python
import pytest
import asyncio
from unittest.mock import Mock, patch
from src.utils.quiz_manager import QuizManager

class TestQuizManager:
    """Test the Islamic quiz system."""
    
    @pytest.fixture
    def quiz_manager(self):
        """Create quiz manager instance for testing."""
        return QuizManager(data_dir="test_data")
    
    def test_islamic_question_loading(self, quiz_manager):
        """Test loading of Islamic knowledge questions."""
        questions = quiz_manager.load_questions()
        assert len(questions) > 0
        assert all("question" in q for q in questions)
        assert all("correct_answer" in q for q in questions)
    
    @pytest.mark.asyncio
    async def test_quiz_session(self, quiz_manager):
        """Test complete quiz session flow."""
        session = await quiz_manager.start_session(user_id=123)
        assert session is not None
        assert session.user_id == 123
```

#### Running Tests
```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_quiz_manager.py

# Run with coverage
python -m pytest tests/ --cov=src/

# Run with verbose output
python -m pytest tests/ -v
```

---

## 🔍 Debugging and Troubleshooting

### 1. Local Development Debugging

#### Enable Debug Logging
```python
# In your development config
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### Use Tree Logging
```python
from src.utils.tree_log import log_perfect_tree_section

log_perfect_tree_section(
    "Debug Information",
    [
        ("feature", "Islamic Quiz System"),
        ("status", "Testing question loading"),
        ("user_id", str(user_id)),
    ],
    "🐛"
)
```

### 2. Common Development Issues

#### Discord Connection Issues
```bash
# Check bot token
echo $DISCORD_TOKEN

# Verify bot permissions in Discord Developer Portal
# Required permissions: Send Messages, Use Slash Commands, Connect, Speak
```

#### Audio Playback Issues
```bash
# Check FFmpeg installation
which ffmpeg
ffmpeg -version

# Verify audio file format
file audio/Saad\ Al\ Ghamdi/001.mp3

# Test audio file
ffplay audio/Saad\ Al\ Ghamdi/001.mp3
```

#### Import Path Issues
```python
# Add src to Python path in development
import sys
sys.path.insert(0, 'src')
```

---

## 🤝 Contributing Guidelines

### 1. Before Contributing

- **Read the Code of Conduct**: Maintain Islamic values and respect
- **Check existing issues**: Avoid duplicate work
- **Discuss major changes**: Open an issue first for large features
- **Test thoroughly**: Ensure your changes don't break existing functionality

### 2. Islamic Development Principles

#### Respect and Dignity
- Use respectful language in all code and comments
- Consider the diverse Muslim community in feature design
- Avoid controversial or divisive implementations

#### Quality and Excellence
- Strive for excellence (Ihsan) in code quality
- Write comprehensive tests
- Document your code thoroughly
- Consider performance and scalability

#### Community Benefit
- Prioritize features that benefit the Muslim community
- Consider accessibility and ease of use
- Think about different Islamic practices and preferences

### 3. Pull Request Process

#### PR Title Format
```
feat: add Islamic feature for community benefit
fix: resolve audio playback issue in Surah recitation
docs: update API documentation with Quranic examples
test: add comprehensive tests for quiz system
```

#### PR Description Template
```markdown
## Description
Brief description of the Islamic feature or fix.

## Islamic Context
How this change benefits the Muslim community or aligns with Islamic values.

## Changes Made
- List of specific changes
- New features added
- Bugs fixed

## Testing
- [ ] Unit tests added/updated
- [ ] Manual testing completed
- [ ] Islamic content verified for accuracy

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Islamic principles respected
```

### 4. Code Review Process

#### For Contributors
- Respond promptly to review feedback
- Be open to suggestions and improvements
- Maintain respectful communication
- Update documentation as needed

#### For Reviewers
- Provide constructive feedback
- Check for Islamic accuracy and sensitivity
- Verify code quality and testing
- Ensure community benefit

---

## 📚 Learning Resources

### 1. Discord.py Documentation
- [Official Discord.py Docs](https://discordpy.readthedocs.io/)
- [Discord Developer Portal](https://discord.com/developers/docs)

### 2. Islamic Resources
- [Quran.com API](https://quran.com/api) for Quranic data
- [Islamic Network APIs](https://aladhan.com/api) for prayer times
- [Hadith Collections](https://sunnah.com/) for authentic sayings

### 3. Python Development
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [pytest Documentation](https://docs.pytest.org/)
- [asyncio Guide](https://docs.python.org/3/library/asyncio.html)

---

## 🔧 Development Tools

### 1. Recommended VS Code Extensions
```json
{
    "recommendations": [
        "ms-python.python",
        "ms-python.black-formatter",
        "ms-python.mypy-type-checker",
        "ms-python.pytest",
        "ms-vscode.vscode-json"
    ]
}
```

### 2. Git Hooks Setup
```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Create .pre-commit-config.yaml
cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/psf/black
    rev: 23.1.0
    hooks:
      - id: black
        language_version: python3
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.0.1
    hooks:
      - id: mypy
EOF
```

### 3. Development Scripts
```bash
# Create development helper scripts
mkdir -p tools/dev

# Format code script
cat > tools/dev/format.sh << 'EOF'
#!/bin/bash
echo "Formatting Python code with black..."
black src/ tests/ tools/
echo "Checking with flake8..."
flake8 src/ tests/ tools/
echo "Type checking with mypy..."
mypy src/
EOF

chmod +x tools/dev/format.sh
```

---

## 🚀 Release Process

### 1. Version Management
```bash
# Update version in src/version.py
echo 'BOT_VERSION = "3.6.0"' > src/version.py

# Create version tag
git tag -a v3.6.0 -m "Release v3.6.0: Enhanced Islamic features"
git push origin v3.6.0
```

### 2. Changelog Updates
```bash
# Update CHANGELOG.md with new features
# Follow semantic versioning (MAJOR.MINOR.PATCH)
```

### 3. Documentation Updates
```bash
# Update API documentation
python tools/update_readme.py

# Verify all documentation is current
# Update deployment guides if needed
```

---

## 💡 Feature Ideas for Contributors

### High Priority Features
1. **Multi-language Support**: Arabic, English, Urdu, Turkish
2. **Prayer Time Integration**: Automated prayer reminders
3. **Hadith Integration**: Daily hadith sharing
4. **Islamic Calendar**: Hijri date display and events
5. **Tafsir Integration**: Verse explanations and context

### Medium Priority Features
1. **Voice Recognition**: Arabic pronunciation checking
2. **Study Groups**: Collaborative Quran study sessions
3. **Progress Tracking**: Personal Islamic learning goals
4. **Community Features**: Islamic discussion forums
5. **Mobile App**: Companion mobile application

### Enhancement Ideas
1. **AI Integration**: Islamic Q&A chatbot
2. **Gamification**: Islamic learning achievements
3. **Social Features**: Islamic community building
4. **Accessibility**: Support for visually impaired users
5. **Performance**: Optimization for large servers

---

## 🤲 Du'a for Developers

*"Our Lord, grant us from Yourself mercy and prepare for us from our affair right guidance."* - **Quran 18:10**

Remember that developing Islamic software is a form of worship and service to the Muslim community. May Allah accept our efforts and make this project a source of benefit for Muslims worldwide.

---

## 📞 Getting Help

### Development Support
- **GitHub Issues**: Report bugs and request features
- **Discussions**: Ask questions and share ideas
- **Discord**: Join our development community (if available)
- **Documentation**: Check existing docs first

### Islamic Guidance
When implementing Islamic features:
- Consult reliable Islamic sources
- Verify Quranic verses and Hadith authenticity
- Consider different schools of Islamic thought
- Seek guidance from Islamic scholars when needed

---

*"And Allah is the best of planners."* - **Quran 8:30**

May your contributions to this Islamic project be a source of continuous reward (sadaqah jariyah) and benefit to the Muslim ummah worldwide. 