# =============================================================================
# QuranBot - Test Configuration and Shared Fixtures
# =============================================================================
# Centralized pytest configuration with shared fixtures, utilities, and
# test setup for comprehensive testing across the QuranBot modernization.
# =============================================================================

import asyncio
from collections.abc import Generator
from datetime import UTC, datetime
import os
from pathlib import Path
import shutil

# Add src to path for imports
import sys
import tempfile
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.config.bot_config import BotConfig
from src.core.di_container import DIContainer
from src.core.structured_logger import StructuredLogger
from src.data.models import (
    AudioServiceConfig,
    BotSession,
    BotStatistics,
    PlaybackPosition,
    PlaybackState,
    StateServiceConfig,
)

# =============================================================================
# Test Configuration
# =============================================================================

# Configure pytest-asyncio
pytest_asyncio.auto_mode = True


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Directory and File Fixtures
# =============================================================================


@pytest.fixture
def temp_directory() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    # Cleanup
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_log_directory(temp_directory: Path) -> Path:
    """Create a temporary log directory structure."""
    log_dir = temp_directory / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Create date-based subdirectory
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    daily_log_dir = log_dir / today
    daily_log_dir.mkdir(parents=True, exist_ok=True)

    return log_dir


@pytest.fixture
def temp_data_directory(temp_directory: Path) -> Path:
    """Create a temporary data directory structure."""
    data_dir = temp_directory / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


@pytest.fixture
def temp_audio_directory(temp_directory: Path) -> Path:
    """Create a temporary audio directory structure."""
    audio_dir = temp_directory / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    # Create reciter subdirectories
    for reciter in ["AbdurRahman_As-Sudais", "Maher_Al_Mueaqly", "Mishary_Rashid"]:
        reciter_dir = audio_dir / reciter
        reciter_dir.mkdir(parents=True, exist_ok=True)

        # Create sample audio files
        for surah in range(1, 4):  # First 3 surahs for testing
            audio_file = reciter_dir / f"{surah:03d}.mp3"
            audio_file.write_text(f"mock audio content for surah {surah}")

    return audio_dir


@pytest.fixture
def temp_backup_directory(temp_directory: Path) -> Path:
    """Create a temporary backup directory structure."""
    backup_dir = temp_directory / "backup"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


# =============================================================================
# Environment and Configuration Fixtures
# =============================================================================


@pytest.fixture
def clean_environment():
    """Provide a clean environment for each test."""
    original_env = os.environ.copy()
    yield
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def valid_config_env(
    temp_directory: Path, temp_audio_directory: Path
) -> dict[str, str]:
    """Provide valid environment configuration for testing."""
    ffmpeg_path = shutil.which("ffmpeg") or "/usr/bin/ffmpeg"

    return {
        "DISCORD_TOKEN": "test_token_1234567890abcdef",
        "GUILD_ID": "123456789012345678",
        "TARGET_CHANNEL_ID": "123456789012345679",
        "CONTROL_CHANNEL_ID": "123456789012345680",
        "PANEL_CHANNEL_ID": "123456789012345681",
        "VOICE_CHANNEL_ID": "123456789012345682",
        "LOG_CHANNEL_ID": "123456789012345683",
        "ADMIN_USER_ID": "123456789012345684",
        "DEVELOPER_ID": "123456789012345684",
        "FFMPEG_PATH": ffmpeg_path,
        "AUDIO_FOLDER": str(temp_audio_directory),
        "DATA_FOLDER": str(temp_directory / "data"),
        "LOG_FOLDER": str(temp_directory / "logs"),
        "BACKUP_FOLDER": str(temp_directory / "backup"),
        "USE_WEBHOOK_LOGGING": "true",
        "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/123/test",
        "BOT_NAME": "TestBot",
        "BOT_VERSION": "1.0.0-test",
        "TIMEZONE": "US/Eastern",
    }


@pytest.fixture
def mock_bot_config(valid_config_env: dict[str, str]) -> Mock:
    """Create a mock BotConfig for testing."""
    config = Mock(spec=BotConfig)
    config.discord_token = valid_config_env["DISCORD_TOKEN"]
    config.guild_id = int(valid_config_env["GUILD_ID"])
    config.target_channel_id = int(valid_config_env["TARGET_CHANNEL_ID"])
    config.control_channel_id = int(valid_config_env["CONTROL_CHANNEL_ID"])
    config.panel_channel_id = int(valid_config_env["PANEL_CHANNEL_ID"])
    config.voice_channel_id = int(valid_config_env["VOICE_CHANNEL_ID"])
    config.log_channel_id = int(valid_config_env["LOG_CHANNEL_ID"])
    config.admin_user_id = int(valid_config_env["ADMIN_USER_ID"])
    config.developer_id = int(valid_config_env["DEVELOPER_ID"])
    config.ffmpeg_path = valid_config_env["FFMPEG_PATH"]
    config.audio_folder = Path(valid_config_env["AUDIO_FOLDER"])
    config.data_folder = Path(valid_config_env["DATA_FOLDER"])
    config.log_folder = Path(valid_config_env["LOG_FOLDER"])
    config.backup_folder = Path(valid_config_env["BACKUP_FOLDER"])
    config.use_webhook_logging = True
    config.discord_webhook_url = valid_config_env["DISCORD_WEBHOOK_URL"]
    config.bot_name = valid_config_env["BOT_NAME"]
    config.bot_version = valid_config_env["BOT_VERSION"]
    config.timezone = valid_config_env["TIMEZONE"]
    return config


# =============================================================================
# Core Service Fixtures
# =============================================================================


@pytest.fixture
def mock_logger() -> Mock:
    """Create a mock StructuredLogger for testing."""
    logger = Mock(spec=StructuredLogger)
    logger.debug = AsyncMock()
    logger.info = AsyncMock()
    logger.warning = AsyncMock()
    logger.error = AsyncMock()
    logger.critical = AsyncMock()
    logger.log_with_context = AsyncMock()
    return logger


@pytest.fixture
def mock_di_container(mock_logger: Mock, mock_bot_config: Mock) -> Mock:
    """Create a mock DI container with common services."""
    container = Mock(spec=DIContainer)
    container.resolve = Mock()

    # Configure common service resolutions
    def resolve_side_effect(interface):
        if interface == StructuredLogger:
            return mock_logger
        elif interface == BotConfig:
            return mock_bot_config
        else:
            return Mock()

    container.resolve.side_effect = resolve_side_effect
    container.register_singleton = Mock()
    container.register_transient = Mock()
    container.is_registered = Mock(return_value=True)

    return container


# =============================================================================
# Discord Mocks
# =============================================================================


@pytest.fixture
def mock_discord_bot() -> Mock:
    """Create a mock Discord bot for testing."""
    bot = Mock()
    bot.user = Mock()
    bot.user.id = 123456789012345678
    bot.user.name = "TestBot"
    bot.get_guild = Mock()
    bot.get_channel = Mock()
    bot.get_user = Mock()
    bot.voice_clients = []
    bot.is_ready = Mock(return_value=True)
    bot.latency = 0.1
    return bot


@pytest.fixture
def mock_discord_guild() -> Mock:
    """Create a mock Discord guild for testing."""
    guild = Mock()
    guild.id = 123456789012345678
    guild.name = "Test Guild"
    guild.get_channel = Mock()
    guild.get_member = Mock()
    guild.voice_client = None
    return guild


@pytest.fixture
def mock_discord_channel() -> Mock:
    """Create a mock Discord channel for testing."""
    channel = Mock()
    channel.id = 123456789012345679
    channel.name = "test-channel"
    channel.guild = Mock()
    channel.guild.id = 123456789012345678
    channel.send = AsyncMock()
    channel.connect = AsyncMock()
    return channel


@pytest.fixture
def mock_discord_voice_client() -> Mock:
    """Create a mock Discord voice client for testing."""
    voice_client = Mock()
    voice_client.is_connected = Mock(return_value=True)
    voice_client.is_playing = Mock(return_value=False)
    voice_client.is_paused = Mock(return_value=False)
    voice_client.disconnect = AsyncMock()
    voice_client.play = Mock()
    voice_client.pause = Mock()
    voice_client.resume = Mock()
    voice_client.stop = Mock()
    voice_client.source = None
    voice_client.volume = 1.0
    return voice_client


@pytest.fixture
def mock_discord_user() -> Mock:
    """Create a mock Discord user for testing."""
    user = Mock()
    user.id = 123456789012345684
    user.name = "TestUser"
    user.display_name = "Test User"
    user.mention = "<@123456789012345684>"
    return user


@pytest.fixture
def mock_discord_interaction(
    mock_discord_user: Mock, mock_discord_guild: Mock, mock_discord_channel: Mock
) -> Mock:
    """Create a mock Discord interaction for testing."""
    interaction = Mock()
    interaction.user = mock_discord_user
    interaction.guild = mock_discord_guild
    interaction.channel = mock_discord_channel
    interaction.response = Mock()
    interaction.response.send_message = AsyncMock()
    interaction.response.defer = AsyncMock()
    interaction.followup = Mock()
    interaction.followup.send = AsyncMock()
    interaction.edit_original_response = AsyncMock()
    return interaction


# =============================================================================
# Data Model Fixtures
# =============================================================================


@pytest.fixture
def sample_playback_state() -> PlaybackState:
    """Create a sample PlaybackState for testing."""
    return PlaybackState(
        is_playing=True,
        is_paused=False,
        is_shuffled=False,
        is_looped=False,
        current_reciter="AbdurRahman_As-Sudais",
        current_surah=1,
        current_file="001.mp3",
        voice_channel_id=123456789012345682,
        guild_id=123456789012345678,
        position=PlaybackPosition(current_seconds=30.5, total_duration=180.0),
        volume=1.0,
        last_updated=datetime.now(UTC),
    )


@pytest.fixture
def sample_bot_session() -> BotSession:
    """Create a sample BotSession for testing."""
    return BotSession(
        session_id="test-session-123",
        start_time=datetime.now(UTC),
        guild_id=123456789012345678,
        voice_channel_id=123456789012345682,
    )


@pytest.fixture
def sample_bot_statistics() -> BotStatistics:
    """Create a sample BotStatistics for testing."""
    return BotStatistics(
        total_sessions=10,
        total_playtime_seconds=3600.0,
        total_commands_executed=50,
        unique_users=5,
        favorite_reciter="AbdurRahman_As-Sudais",
        favorite_surah=2,
        last_reset=datetime.now(UTC),
    )


# =============================================================================
# Service Configuration Fixtures
# =============================================================================


@pytest.fixture
def audio_service_config(temp_audio_directory: Path) -> AudioServiceConfig:
    """Create AudioServiceConfig for testing."""
    return AudioServiceConfig(
        audio_folder=temp_audio_directory,
        ffmpeg_path="/usr/bin/ffmpeg",
        default_volume=1.0,
        connection_timeout=30.0,
        playback_timeout=300.0,
        max_retry_attempts=3,
        retry_delay=1.0,
    )


@pytest.fixture
def state_service_config(
    temp_data_directory: Path, temp_backup_directory: Path
) -> StateServiceConfig:
    """Create StateServiceConfig for testing."""
    return StateServiceConfig(
        data_directory=temp_data_directory,
        backup_directory=temp_backup_directory,
        backup_interval_hours=1,
        max_backups=5,
        compression_enabled=True,
        validation_enabled=True,
    )


# =============================================================================
# Async Test Utilities
# =============================================================================


@pytest.fixture
async def async_test_timeout() -> float:
    """Default timeout for async tests."""
    return 5.0


class AsyncContextManager:
    """Helper for creating async context managers in tests."""

    def __init__(self, return_value=None):
        self.return_value = return_value

    async def __aenter__(self):
        return self.return_value

    async def __aaenter__(self):
        pass


@pytest.fixture
def async_context_manager():
    """Factory for creating async context managers in tests."""
    return AsyncContextManager


# =============================================================================
# Test Utilities and Helpers
# =============================================================================


class TestDataFactory:
    """Factory for creating test data objects."""

    @staticmethod
    def create_mock_audio_file_info(
        surah: int = 1, reciter: str = "Test_Reciter"
    ) -> dict[str, Any]:
        """Create mock audio file info."""
        return {
            "surah": surah,
            "reciter": reciter,
            "file_path": f"/test/audio/{reciter}/{surah:03d}.mp3",
            "duration": 180.0,
            "size": 5242880,  # 5MB
            "bitrate": 128,
            "last_modified": datetime.now(UTC).isoformat(),
        }

    @staticmethod
    def create_mock_quiz_question() -> dict[str, Any]:
        """Create mock quiz question."""
        return {
            "question": "What is the first Surah of the Quran?",
            "choices": ["Al-Fatiha", "Al-Baqarah", "Al-Imran", "An-Nisa"],
            "correct_answer": 0,
            "difficulty": "easy",
            "category": "quran_knowledge",
            "explanation": "Al-Fatiha is the opening chapter of the Quran.",
        }


@pytest.fixture
def test_data_factory() -> TestDataFactory:
    """Provide test data factory for creating mock objects."""
    return TestDataFactory()


# =============================================================================
# Performance and Resource Testing
# =============================================================================


@pytest.fixture
def performance_test_config() -> dict[str, Any]:
    """Configuration for performance tests."""
    return {
        "max_execution_time": 1.0,  # 1 second
        "max_memory_usage": 50 * 1024 * 1024,  # 50MB
        "concurrent_operations": 10,
        "stress_test_iterations": 100,
    }


@pytest.fixture
def resource_monitor():
    """Monitor resource usage during tests."""
    import time

    import psutil

    class ResourceMonitor:
        def __init__(self):
            self.process = psutil.Process()
            self.start_memory = None
            self.start_time = None

        def start(self):
            self.start_memory = self.process.memory_info().rss
            self.start_time = time.time()

        def stop(self):
            end_memory = self.process.memory_info().rss
            end_time = time.time()
            return {
                "memory_used": end_memory - self.start_memory,
                "execution_time": end_time - self.start_time,
            }

    return ResourceMonitor()


# =============================================================================
# Cleanup and Teardown
# =============================================================================


@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Automatic cleanup after each test."""
    yield
    # Cleanup any global state, close connections, etc.
    import gc

    gc.collect()
