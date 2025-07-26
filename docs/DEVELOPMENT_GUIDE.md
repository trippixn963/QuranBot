# 🛠️ QuranBot Modernized Development Guide

This guide covers local development setup and best practices for the modernized QuranBot architecture with dependency injection, type-safe configuration, structured logging, and comprehensive testing.

## 🎯 Architecture Overview

### **Modern Architecture Stack**

```
┌─────────────────────────────────────────────────────────────┐
│                     Discord Bot (main_modernized.py)        │
├─────────────────────────────────────────────────────────────┤
│                 Dependency Injection Container              │
├─────────────────┬─────────────────┬─────────────────────────┤
│   Core Services │  Modern Services│    Utility Services     │
├─────────────────┼─────────────────┼─────────────────────────┤
│ • CacheService  │ • AudioService  │ • RichPresenceManager   │
│ • PerformanceM. │ • StateService  │ • ControlPanel          │
│ • ResourceMgr   │ • MetadataCache │ • QuizManager           │
│ • SecuritySvc   │                 │ • DailyVerses           │
│ • StructuredLog │                 │                         │
└─────────────────┴─────────────────┴─────────────────────────┘
```

### **Key Principles**

- **Dependency Injection**: All services are injected through DIContainer
- **Service Isolation**: Each service has a specific responsibility
- **Configuration Management**: Environment-based configuration
- **Structured Logging**: JSON-based logging throughout
- **Performance Monitoring**: Built-in metrics and profiling
- **Testing**: Comprehensive test coverage with mocking

## 🚀 Development Setup

### **Prerequisites**

- **Python**: 3.11+ (required for modern type hints and features)
- **Poetry**: Latest version for dependency management
- **Git**: Version control
- **FFmpeg**: Audio processing (for local testing)
- **Docker**: Optional, for containerized development
- **IDE**: VS Code or PyCharm recommended with Python extensions
- **Discord Bot**: Test bot token for development

### **Local Environment Setup**

#### **1. Clone and Setup**

```bash
# Clone repository
git clone https://github.com/trippixn963/QuranBot.git
cd QuranBot

# Create virtual environment with Python 3.11+
python3.11 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate     # Windows

# Verify Python version
python --version  # Should be 3.11+

# Install Poetry (if not already installed)
curl -sSL https://install.python-poetry.org | python3 -
export PATH="$HOME/.local/bin:$PATH"

# Install all dependencies (including dev dependencies)
poetry install

# Verify installation
poetry show | grep -E "(discord|pydantic|pytest)"
```

#### **2. Development Configuration**

```bash
# Copy environment template
cp config/.env.example config/.env

# Edit for development
nano config/.env
```

**Development Configuration Example:**

```bash
# =============================================================================
# QuranBot Development Configuration
# =============================================================================

# Environment
ENVIRONMENT=development

# Discord Configuration (use test bot token)
DISCORD_TOKEN=YOUR_DEV_BOT_TOKEN
GUILD_ID=YOUR_TEST_SERVER_ID

# Use your personal user ID for development
ADMIN_USER_ID=YOUR_USER_ID
DEVELOPER_ID=YOUR_USER_ID
PANEL_ACCESS_ROLE_ID=YOUR_DEV_ROLE_ID

# Development channels (create test channels)
TARGET_CHANNEL_ID=YOUR_DEV_VOICE_CHANNEL
PANEL_CHANNEL_ID=YOUR_DEV_TEXT_CHANNEL
LOGS_CHANNEL_ID=YOUR_DEV_LOG_CHANNEL
DAILY_VERSE_CHANNEL_ID=YOUR_DEV_VERSE_CHANNEL

# Audio Configuration (local paths)
AUDIO_FOLDER=audio
DEFAULT_RECITER=Saad Al Ghamdi
AUDIO_QUALITY=128k
DEFAULT_SHUFFLE=false
DEFAULT_LOOP=false
FFMPEG_PATH=/opt/homebrew/bin/ffmpeg  # macOS with Homebrew
# FFMPEG_PATH=/usr/bin/ffmpeg         # Linux
# FFMPEG_PATH=C:\ffmpeg\bin\ffmpeg.exe # Windows

# Development Performance Settings
CACHE_TTL=60                    # Shorter cache for development
MAX_CONCURRENT_AUDIO=1
BACKUP_INTERVAL_HOURS=1         # More frequent backups for testing

# Development Security Settings
RATE_LIMIT_PER_MINUTE=100       # Higher limit for testing

# Development Logging
LOG_LEVEL=DEBUG                 # Verbose logging for development
USE_WEBHOOK_LOGGING=true        # Optional: webhook logging
DISCORD_WEBHOOK_URL=YOUR_DEV_WEBHOOK_URL

# VPS Configuration (not needed for local development)
# VPS_HOST=localhost
```

#### **3. Install FFmpeg**

```bash
# macOS (Homebrew)
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows (using Chocolatey)
choco install ffmpeg

# Verify installation
ffmpeg -version
```

#### **4. Validate Configuration**

```bash
# Test configuration loading
python -c "
from src.config.config_service import ConfigService
try:
    config_service = ConfigService()
    print('✅ Configuration loaded successfully')
    print(f'Guild ID: {config_service.config.GUILD_ID}')
    print(f'Audio Folder: {config_service.config.AUDIO_FOLDER}')
    print(f'Environment: {config_service.config.ENVIRONMENT}')
except Exception as e:
    print(f'❌ Configuration error: {e}')
"

# Test Discord token (optional)
python -c "
import discord
import asyncio
from src.config.config_service import ConfigService

async def test_token():
    try:
        config = ConfigService().config
        client = discord.Client(intents=discord.Intents.default())
        await client.login(config.DISCORD_TOKEN)
        print('✅ Discord token is valid')
        await client.close()
    except Exception as e:
        print(f'❌ Discord token test failed: {e}')

asyncio.run(test_token())
"
```

## 🏗️ Development Workflow

### **Running the Bot**

#### **Standard Development Mode**

```bash
# Activate environment
source .venv/bin/activate

# Run with full logging
python main_modernized.py

# Or with specific log level
LOG_LEVEL=DEBUG python main_modernized.py
```

#### **Testing Mode**

```bash
# Run tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src --cov-report=html

# Run specific test module
poetry run pytest tests/test_audio_service.py -v

# Run integration tests
poetry run pytest tests/test_integration_comprehensive.py -v
```

#### **Debug Mode**

```bash
# Use the debug script for isolated testing
python debug_bot.py

# Or test individual services
python -c "
from src.core.di_container import DIContainer
container = DIContainer()
print('DI Container initialized successfully')
"
```

### **Code Structure**

#### **Service Development Pattern**

```python
# Example: Creating a new service
from typing import Optional
from src.core.di_container import DIContainer
from src.core.structured_logger import StructuredLogger

class MyNewService:
    def __init__(
        self,
        container: DIContainer,
        logger: StructuredLogger,
        config: dict
    ):
        self.container = container
        self.logger = logger
        self.config = config
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize the service."""
        try:
            # Service initialization logic
            await self.logger.info("MyNewService initializing")
            self._initialized = True
            return True
        except Exception as e:
            await self.logger.error("Failed to initialize MyNewService", {
                "error": str(e)
            })
            return False

    async def shutdown(self):
        """Graceful shutdown."""
        if self._initialized:
            await self.logger.info("MyNewService shutting down")
            self._initialized = False
```

#### **Dependency Injection Usage**

```python
# Register service in DIContainer
def setup_services(container: DIContainer):
    # Register as singleton
    container.register_singleton(MyNewService, lambda: MyNewService(
        container=container,
        logger=container.get(StructuredLogger),
        config={"key": "value"}
    ))

# Use service in other components
class SomeOtherService:
    def __init__(self, container: DIContainer):
        self.my_service = container.get(MyNewService)
```

### **Testing Guidelines**

#### **Unit Testing**

```python
import pytest
from unittest.mock import AsyncMock, Mock
from src.services.my_new_service import MyNewService

@pytest.fixture
def mock_container():
    container = Mock()
    return container

@pytest.fixture
def mock_logger():
    logger = AsyncMock()
    return logger

@pytest.mark.asyncio
async def test_my_service_initialization(mock_container, mock_logger):
    service = MyNewService(
        container=mock_container,
        logger=mock_logger,
        config={"test": True}
    )

    result = await service.initialize()
    assert result is True
    assert service._initialized is True
    mock_logger.info.assert_called_once()
```

#### **Integration Testing**

```python
@pytest.mark.asyncio
async def test_full_service_integration():
    """Test complete service integration."""
    from src.core.di_container import DIContainer

    container = DIContainer()
    # Setup all required services

    # Test service interactions
    audio_service = container.get(AudioService)
    state_service = container.get(StateService)

    # Test cross-service functionality
    await audio_service.initialize()
    await state_service.initialize()

    # Cleanup
    await audio_service.shutdown()
    await state_service.shutdown()
```

## 🔧 Development Tools

### **Code Quality**

```bash
# Format code
poetry run black src/ tests/

# Lint code
poetry run flake8 src/ tests/

# Type checking
poetry run mypy src/

# Security scanning
poetry run bandit -r src/

# Run all quality checks
poetry run pre-commit run --all-files
```

### **Performance Profiling**

```python
# Use built-in performance monitor
from src.core.performance_monitor import PerformanceMonitor

async def profile_function():
    monitor = PerformanceMonitor(...)
    await monitor.initialize()

    with monitor.profile_context("my_function"):
        # Your code here
        pass

    metrics = await monitor.get_system_metrics()
    print(f"CPU: {metrics.cpu_percent}%")
```

### **Logging Development**

```python
# Structured logging example
await logger.info("Service operation", {
    "service": "AudioService",
    "operation": "play_surah",
    "surah_number": 1,
    "duration_ms": 150,
    "user_id": 12345
})

# Error logging with context
await logger.error("Operation failed", {
    "error": str(exception),
    "error_type": type(exception).__name__,
    "context": {"surah": 1, "user": 12345}
})
```

## 🛠️ Service Development

### **Creating New Services**

#### **1. Service Template**

```python
# src/services/my_service.py
from typing import Optional, Dict, Any
from src.core.di_container import DIContainer
from src.core.structured_logger import StructuredLogger

class MyService:
    """
    Service description and purpose.

    This service handles specific functionality and integrates
    with other services through dependency injection.
    """

    def __init__(
        self,
        container: DIContainer,
        logger: StructuredLogger,
        config: Dict[str, Any]
    ):
        self.container = container
        self.logger = logger
        self.config = config
        self._state = {}

    async def initialize(self) -> bool:
        """Initialize service with dependencies."""
        try:
            await self.logger.info("Initializing MyService")
            # Initialization logic here
            return True
        except Exception as e:
            await self.logger.error("MyService initialization failed", {
                "error": str(e)
            })
            return False

    async def shutdown(self):
        """Graceful shutdown with cleanup."""
        await self.logger.info("Shutting down MyService")
        # Cleanup logic here
```

#### **2. Register Service**

```python
# In main_modernized.py or service setup
def setup_my_service(container: DIContainer):
    config = {"setting": "value"}

    my_service_factory = lambda: MyService(
        container=container,
        logger=container.get(StructuredLogger),
        config=config
    )

    container.register_singleton(MyService, my_service_factory)
```

#### **3. Write Tests**

```python
# tests/test_my_service.py
import pytest
from unittest.mock import AsyncMock, Mock
from src.services.my_service import MyService

class TestMyService:
    @pytest.fixture
    def service(self):
        container = Mock()
        logger = AsyncMock()
        config = {"test": True}
        return MyService(container, logger, config)

    @pytest.mark.asyncio
    async def test_initialization(self, service):
        result = await service.initialize()
        assert result is True
        service.logger.info.assert_called()
```

### **Service Integration Patterns**

#### **Event-Driven Communication**

```python
class ServiceA:
    async def emit_event(self, event_type: str, data: dict):
        """Emit event to other services."""
        event_bus = self.container.get(EventBus)
        await event_bus.emit(event_type, data)

class ServiceB:
    async def initialize(self):
        """Subscribe to events from other services."""
        event_bus = self.container.get(EventBus)
        event_bus.subscribe("audio_started", self.on_audio_started)

    async def on_audio_started(self, data: dict):
        """Handle audio start event."""
        await self.logger.info("Audio started", data)
```

## 🧪 Testing Strategies

### **Test Organization**

```
tests/
├── unit/           # Isolated unit tests
│   ├── test_cache_service.py
│   ├── test_audio_service.py
│   └── ...
├── integration/    # Service integration tests
│   ├── test_audio_state_integration.py
│   └── ...
├── e2e/           # End-to-end tests
│   ├── test_bot_startup.py
│   └── ...
├── fixtures/      # Test data and fixtures
└── conftest.py    # Pytest configuration
```

### **Mocking Strategies**

```python
# Mock Discord bot
@pytest.fixture
def mock_bot():
    bot = AsyncMock()
    bot.latency = 0.05
    bot.user.name = "TestBot"
    return bot

# Mock container with services
@pytest.fixture
def container_with_mocks():
    container = DIContainer()

    # Register mock services
    container.register_singleton(StructuredLogger, AsyncMock())
    container.register_singleton(CacheService, AsyncMock())

    return container
```

## 📊 Monitoring & Debugging

### **Local Monitoring**

```bash
# Monitor log files
tail -f logs/quranbot.log | jq '.'

# Monitor performance
python -c "
from src.core.performance_monitor import PerformanceMonitor
import asyncio

async def monitor():
    pm = PerformanceMonitor(...)
    metrics = await pm.get_system_metrics()
    print(f'CPU: {metrics.cpu_percent}%')
    print(f'Memory: {metrics.memory_percent}%')

asyncio.run(monitor())
"
```

### **Debugging Tools**

```python
# Interactive debugging
import pdb; pdb.set_trace()

# Async debugging
import ipdb; ipdb.set_trace()

# Rich debugging with context
from rich.console import Console
console = Console()

async def debug_service_state(service):
    console.print("[bold]Service State Debug[/bold]")
    console.print(f"Initialized: {service._initialized}")
    console.print(f"State: {service._state}")
```

## 🚀 Contributing Guidelines

### **Code Standards**

- **Python**: Follow PEP 8 with Black formatting
- **Type Hints**: Required for all public methods
- **Docstrings**: Google-style docstrings for all classes/methods
- **Async/Await**: Use async patterns consistently
- **Error Handling**: Comprehensive error handling with logging

### **Commit Convention**

```bash
# Feature commits
git commit -m "feat(audio): add advanced caching for metadata"

# Bug fixes
git commit -m "fix(state): resolve persistence issue on shutdown"

# Documentation
git commit -m "docs(dev): update development setup guide"

# Tests
git commit -m "test(integration): add comprehensive audio service tests"
```

### **Pull Request Process**

1. **Create Feature Branch**: `git checkout -b feature/my-feature`
2. **Implement Changes**: Follow coding standards
3. **Add Tests**: Ensure >90% test coverage
4. **Update Documentation**: Update relevant docs
5. **Run Quality Checks**: `poetry run pre-commit run --all-files`
6. **Submit PR**: Detailed description with testing notes

## 📚 Additional Resources

- **[Architecture Documentation](ARCHITECTURE.md)**: Detailed architecture overview
- **[API Reference](API_REFERENCE.md)**: Service and method documentation
- **[Deployment Guide](DEPLOYMENT_GUIDE.md)**: Production deployment
- **[Troubleshooting Guide](TROUBLESHOOTING.md)**: Common development issues

## 🎯 Development Best Practices

### **Performance**

- Use async/await consistently
- Implement proper caching strategies
- Monitor resource usage during development
- Profile critical code paths

### **Security**

- Never commit real tokens/credentials
- Use environment variables for all config
- Implement proper input validation
- Follow principle of least privilege

### **Maintainability**

- Keep services focused and small
- Use dependency injection consistently
- Write comprehensive tests
- Document complex business logic

---

**🛠️ Happy coding with the modernized QuranBot architecture!**
