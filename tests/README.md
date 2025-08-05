# QuranBot Test Suite

Comprehensive test suite for QuranBot with categorized test modules covering all core functionality, services, and error handling.

## 📁 Test Structure

```
tests/
├── __init__.py              # Test package initialization
├── conftest.py              # Pytest configuration and fixtures
├── run_tests.py             # Test runner script
├── README.md               # This file
├── test_core_config.py     # Configuration management tests
├── test_core_logging.py    # Logging system tests
├── test_core_errors.py     # Error handling tests
├── test_services_base.py   # Base service tests
└── test_bot.py             # Main bot functionality tests
```

## 🏷️ Test Categories

### Core Functionality
- **Configuration** (`@pytest.mark.config`): Configuration management, validation, and environment settings
- **Logging** (`@pytest.mark.logging`): Tree logger, log retention, performance tracking
- **Errors** (`@pytest.mark.errors`): Error handling, categorization, retry mechanisms

### Services
- **Base Service** (`@pytest.mark.services`): Service lifecycle, health monitoring, retry mechanisms
- **Audio Service** (`@pytest.mark.audio`): Audio playback, voice management
- **Database Service** (`@pytest.mark.database`): Data persistence, queries
- **State Service** (`@pytest.mark.state`): State management, persistence
- **Metadata Cache** (`@pytest.mark.metadata`): Caching, performance

### Bot Functionality
- **Bot** (`@pytest.mark.bot`): Main bot class, event handling, service management
- **Commands** (`@pytest.mark.commands`): Discord slash commands
- **Events** (`@pytest.mark.events`): Discord event handling

### Test Types
- **Unit** (`@pytest.mark.unit`): Individual component tests
- **Integration** (`@pytest.mark.integration`): Component interaction tests
- **Performance** (`@pytest.mark.performance`): Performance and load tests
- **Reliability** (`@pytest.mark.reliability`): Error recovery and stability tests

## 🚀 Quick Start

### Prerequisites
```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov pytest-xdist

# Optional: Install additional test tools
pip install pytest-html pytest-json-report
```

### Running Tests

#### Using the Test Runner
```bash
# Run all tests
python tests/run_tests.py

# Run specific test categories
python tests/run_tests.py --core
python tests/run_tests.py --services
python tests/run_tests.py --bot

# Run with coverage
python tests/run_tests.py --coverage

# Run in parallel
python tests/run_tests.py --parallel

# Run specific test types
python tests/run_tests.py --unit
python tests/run_tests.py --integration
```

#### Using Pytest Directly
```bash
# Run all tests
pytest tests/

# Run specific categories
pytest -m "config or logging"
pytest -m "services"
pytest -m "bot"

# Run with coverage
pytest --cov=app --cov-report=html tests/

# Run in parallel
pytest -n auto tests/

# Run specific test file
pytest tests/test_core_config.py
```

## 📊 Test Coverage

### Current Coverage Areas

#### ✅ Fully Tested
- Configuration management and validation
- Error handling and categorization
- Base service lifecycle
- Logging system components
- Bot initialization and event handling

#### 🔄 Partially Tested
- Service-specific functionality (audio, database, state)
- Discord command handling
- Integration scenarios

#### 📋 Planned Tests
- Audio service playback functionality
- Database service operations
- State management persistence
- Discord command interactions
- Performance benchmarks
- Reliability stress tests

## 🧪 Test Examples

### Configuration Tests
```python
@pytest.mark.config
@pytest.mark.unit
def test_config_creation_with_valid_data(self):
    """Test creating configuration with valid data."""
    config = QuranBotConfig(
        discord_token="test_token_12345",
        guild_id=123456789,
        voice_channel_id=987654321,
        panel_channel_id=555666777
    )
    
    assert config.discord_token == "test_token_12345"
    assert config.guild_id == 123456789
```

### Error Handling Tests
```python
@pytest.mark.errors
@pytest.mark.unit
async def test_safe_execute_with_retry(self):
    """Test safe execution with retry logic."""
    handler = ErrorHandler()
    
    call_count = 0
    async def failing_operation():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("Temporary failure")
        return "success"
    
    result = await handler.safe_execute(
        failing_operation,
        {"operation": "test", "service": "test_service"},
        max_retries=3
    )
    
    assert result == "success"
    assert call_count == 3
```

### Service Tests
```python
@pytest.mark.services
@pytest.mark.unit
async def test_service_lifecycle(self):
    """Test complete service lifecycle."""
    service = MockService("TestService")
    
    await service.initialize()
    assert service.state == ServiceState.INITIALIZED
    
    await service.start()
    assert service.state == ServiceState.RUNNING
    
    await service.stop()
    assert service.state == ServiceState.STOPPED
    
    await service.cleanup()
    assert service.state == ServiceState.CLEANED_UP
```

## 🔧 Test Configuration

### Pytest Configuration (`pytest.ini`)
- **Test Discovery**: Automatically finds test files in `tests/`
- **Markers**: Predefined markers for test categorization
- **Async Support**: Automatic async test detection and execution
- **Output**: Short tracebacks, duration reporting, max failures

### Test Runner Features
- **Category Selection**: Run specific test categories
- **Coverage Reporting**: HTML and terminal coverage reports
- **Parallel Execution**: Run tests in parallel for speed
- **Output Formats**: JUnit XML, HTML reports
- **Verbose Output**: Detailed test execution information

## 📈 Coverage Reports

### HTML Coverage Report
```bash
# Generate HTML coverage report
pytest --cov=app --cov-report=html tests/
# Open htmlcov/index.html in browser
```

### Terminal Coverage Report
```bash
# Show coverage in terminal
pytest --cov=app --cov-report=term-missing tests/
```

### Coverage Configuration
```ini
# In pytest.ini
addopts = --cov=app --cov-report=html --cov-report=term-missing
```

## 🐛 Debugging Tests

### Verbose Output
```bash
# Show detailed test output
pytest -v tests/

# Show even more detail
pytest -vv tests/
```

### Test Selection
```bash
# Run specific test function
pytest tests/test_core_config.py::TestConfiguration::test_config_creation_with_valid_data

# Run tests matching pattern
pytest -k "config" tests/

# Run tests with specific marker
pytest -m "unit" tests/
```

### Debug Mode
```bash
# Run with debugger
pytest --pdb tests/

# Stop on first failure
pytest -x tests/

# Show local variables on failure
pytest -l tests/
```

## 🔄 Continuous Integration

### GitHub Actions Example
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov
      - name: Run tests
        run: |
          python tests/run_tests.py --coverage
      - name: Upload coverage
        uses: codecov/codecov-action@v1
```

## 📝 Adding New Tests

### Test File Structure
```python
# =============================================================================
# QuranBot - Test Category
# =============================================================================
# Description of what this test module covers
# =============================================================================

import pytest
from unittest.mock import Mock, AsyncMock, patch

class TestFeature:
    """Test feature functionality."""
    
    @pytest.mark.category
    @pytest.mark.unit
    def test_feature_functionality(self):
        """Test specific feature functionality."""
        # Test implementation
        pass
    
    @pytest.mark.category
    @pytest.mark.integration
    async def test_feature_integration(self):
        """Test feature integration."""
        # Integration test implementation
        pass
```

### Test Guidelines
1. **Naming**: Use descriptive test names that explain what is being tested
2. **Markers**: Always use appropriate pytest markers
3. **Documentation**: Include docstrings explaining test purpose
4. **Isolation**: Each test should be independent and not rely on other tests
5. **Mocking**: Use mocks for external dependencies
6. **Async**: Use `async def` for async tests
7. **Edge Cases**: Include tests for error conditions and edge cases

### Fixtures
```python
@pytest.fixture
def mock_service():
    """Create a mock service for testing."""
    service = Mock()
    service.initialize = AsyncMock()
    service.start = AsyncMock()
    service.stop = AsyncMock()
    return service
```

## 🚨 Common Issues

### Import Errors
```bash
# Ensure PYTHONPATH includes project root
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Async Test Issues
```python
# Use pytest-asyncio for async tests
@pytest.mark.asyncio
async def test_async_function():
    # Test implementation
    pass
```

### Mock Issues
```python
# Use AsyncMock for async methods
mock_service.some_async_method = AsyncMock(return_value="result")
```

## 📚 Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest-Asyncio](https://pytest-asyncio.readthedocs.io/)
- [Pytest-Cov](https://pytest-cov.readthedocs.io/)
- [Python Testing Best Practices](https://realpython.com/python-testing/)

## 🤝 Contributing

When adding new tests:
1. Follow the existing test structure and naming conventions
2. Use appropriate pytest markers
3. Include both unit and integration tests
4. Add tests for error conditions and edge cases
5. Update this README if adding new test categories
6. Ensure all tests pass before submitting

## 📊 Test Statistics

- **Total Test Files**: 5
- **Total Test Functions**: 150+
- **Coverage Target**: 90%+
- **Test Categories**: 8
- **Markers**: 15+

---

*This test suite ensures QuranBot maintains high quality and reliability through comprehensive testing of all components.* 