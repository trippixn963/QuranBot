# 🤝 Contributing to QuranBot

Thank you for your interest in contributing to QuranBot! This project serves the Islamic community with 24/7 Quran recitation and interactive Islamic learning features. We welcome contributions from developers of all backgrounds and faiths.

## 🌟 **Ways to Contribute**

### 🐛 **Bug Reports**
- Use GitHub Issues to report bugs
- Include detailed reproduction steps
- Provide system information (OS, Python version, etc.)
- Include relevant log outputs

### 💡 **Feature Requests**
- Suggest new Islamic learning features
- Propose technical improvements
- Request additional reciter support
- Suggest UI/UX enhancements

### 🔧 **Code Contributions**
- Fix bugs and issues
- Add new features
- Improve performance
- Enhance documentation
- Write tests

### 📚 **Documentation**
- Improve installation guides
- Add usage examples
- Update API documentation
- Translate documentation

## 🚀 **Getting Started**

### **Prerequisites**
- Python 3.9+
- FFmpeg installed
- Discord.py knowledge (helpful)
- Git basics

### **Development Setup**
```bash
# 1. Fork the repository on GitHub

# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/QuranBot.git
cd QuranBot

# 3. Create development branch
git checkout -b feature/your-feature-name

# 4. Set up virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 5. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies

# 6. Copy configuration
cp config/.env.example config/.env
# Edit config/.env with your test bot credentials

# 7. Run tests
python -m pytest tests/

# 8. Start development server
python main.py
```

## 📋 **Development Guidelines**

### **Code Standards**
- **Documentation**: Follow Google-style docstrings (98% consistency maintained)
- **Type Hints**: Use type hints for all functions and methods
- **Error Handling**: Comprehensive exception handling with context
- **Async/Await**: Use async patterns consistently
- **Dependency Injection**: Follow existing DI container patterns

### **Architecture Principles**
- **Separation of Concerns**: Keep audio, UI, and data layers separate
- **Enterprise Patterns**: Use existing service patterns and interfaces
- **Performance**: Maintain the 60% CPU reduction through unified scheduling
- **Reliability**: Follow existing recovery and error handling patterns

### **File Organization**
```
src/
├── commands/          # Discord slash commands
├── core/             # Core infrastructure (DI, logging, etc.)
├── services/         # Business logic services
├── utils/            # Utility functions and helpers
├── config/           # Configuration management
└── data/             # Data models and schemas
```

## 🧪 **Testing**

### **Test Categories**
- **Unit Tests**: Individual component testing
- **Integration Tests**: Service interaction testing
- **Audio Tests**: Audio streaming and recovery
- **Discord Tests**: Bot command and interaction testing

### **Running Tests**
```bash
# Run all tests
python -m pytest

# Run specific test category
python -m pytest tests/test_audio_manager.py

# Run with coverage
python -m pytest --cov=src tests/

# Run integration tests
python -m pytest tests/test_integration.py -v
```

### **Test Requirements**
- Write tests for new features
- Maintain or improve test coverage
- Test both success and failure scenarios
- Include async test patterns where appropriate

## 📝 **Code Style**

### **Formatting**
- **Line Length**: 88 characters (Black formatter standard)
- **Indentation**: 4 spaces (no tabs)
- **Imports**: Organized (standard → third-party → local)
- **Trailing Commas**: Use in multi-line structures

### **Naming Conventions**
- **Functions/Variables**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_CASE`
- **Private Methods**: `_leading_underscore`

### **Documentation Standards**
```python
class ExampleService:
    """Brief description of the service.

    Detailed explanation of the service's purpose, key features,
    and how it integrates with the rest of the system.

    Attributes:
        attribute_name: Description of the attribute

    Example:
        Basic usage example:

        ```python
        service = ExampleService()
        result = await service.do_something()
        ```
    """

    async def example_method(
        self,
        param1: str,
        param2: int = 10
    ) -> Dict[str, Any]:
        """Brief description of what the method does.

        Longer explanation if needed, including algorithm details,
        performance considerations, or integration points.

        Args:
            param1: Description of param1
            param2: Description of param2 with default value

        Returns:
            Dictionary containing the results with keys:
            - key1: Description of key1
            - key2: Description of key2

        Raises:
            ValueError: When param1 is invalid
            ConnectionError: When unable to connect to Discord

        Note:
            Any important notes about usage, performance, or side effects.
        """
        pass
```

## 🔄 **Pull Request Process**

### **Before Submitting**
1. **Test Thoroughly**: Ensure all tests pass
2. **Documentation**: Update relevant documentation
3. **Code Quality**: Run linting and formatting
4. **Islamic Sensitivity**: Ensure respectful handling of Islamic content

### **PR Requirements**
- **Descriptive Title**: Clear summary of changes
- **Detailed Description**: What, why, and how of your changes
- **Issue Reference**: Link to related issues if applicable
- **Test Coverage**: Include or update tests
- **Documentation**: Update docs for new features

### **PR Template**
```markdown
## Description
Brief description of what this PR does.

## Type of Change
- [ ] Bug fix (non-breaking change)
- [ ] New feature (non-breaking change)
- [ ] Breaking change (fix or feature causing existing functionality to change)
- [ ] Documentation update

## Changes Made
- List specific changes made
- Include any new dependencies
- Mention any configuration changes

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] New tests written (if applicable)

## Islamic Content Considerations
- [ ] Respectful handling of Quran content
- [ ] Appropriate Arabic text handling
- [ ] Islamic knowledge accuracy verified

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] No sensitive information exposed
```

## 🎯 **Contribution Areas**

### **High Priority**
- **Audio System Improvements**: Better codec support, quality enhancements
- **Islamic Learning Features**: More quiz categories, Hadith integration
- **Performance Optimization**: Further CPU and memory improvements
- **Mobile Discord Support**: Better mobile interaction patterns

### **Medium Priority**
- **Additional Languages**: Support for more translation languages
- **Prayer Time Features**: Multiple city support, custom locations
- **Community Features**: User profiles, achievement systems
- **Analytics**: Better usage analytics and insights

### **Technical Improvements**
- **Database Migration**: Advanced schema migration support
- **Monitoring**: Enhanced health monitoring and alerting
- **Docker**: Multi-architecture container support
- **CI/CD**: Automated testing and deployment pipelines

## 🌍 **Islamic Content Guidelines**

### **Respectful Implementation**
- **Accuracy**: Ensure Islamic content accuracy
- **Sensitivity**: Handle religious content with appropriate respect
- **Authentication**: Use authentic Quran and Hadith sources
- **Cultural Awareness**: Consider diverse Islamic cultural practices

### **Content Sources**
- **Quran**: Use authenticated Quran text sources
- **Hadith**: Reference authentic Hadith collections
- **Islamic Knowledge**: Verify accuracy with Islamic scholars when needed
- **Translations**: Use respected translation sources

## 🤝 **Community Guidelines**

### **Code of Conduct**
- **Respectful Communication**: Treat all contributors with respect
- **Interfaith Dialogue**: Welcome contributors from all backgrounds
- **Islamic Sensitivity**: Maintain respect for Islamic content and community
- **Collaborative Spirit**: Work together toward common goals

### **Getting Help**
- **GitHub Discussions**: Ask questions and share ideas
- **Issues**: Report bugs and request features
- **Discord Server**: Join our community at [discord.gg/syria](https://discord.gg/syria)
- **Documentation**: Check existing documentation first

## 📞 **Contact**

### **Maintainers**
- Primary maintainer information will be updated here
- Additional core contributor contact information

### **Community**
- **GitHub Issues**: Technical questions and bug reports
- **GitHub Discussions**: General questions and ideas
- **Discord Community**: Real-time community interaction at [discord.gg/syria](https://discord.gg/syria)

## 🎉 **Recognition**

### **Contributors**
All contributors will be recognized in:
- **README.md**: Contributors section
- **Release Notes**: Feature contribution acknowledgments
- **GitHub**: Contributor graphs and statistics

### **Types of Contributions Recognized**
- Code contributions
- Documentation improvements
- Bug reports and testing
- Islamic content verification
- Community support and moderation
- Translation work

---

## 🙏 **Thank You**

Thank you for considering contributing to QuranBot! Your contributions help serve the Islamic community and create a bridge of understanding between different faiths through technology.

**"And whoever saves a life, it is as if he has saved all of mankind."** - *Quran 5:32*

Together, we can build something beautiful that serves the Islamic community while fostering interfaith understanding and collaboration.

---

**Happy Contributing! 🚀**
