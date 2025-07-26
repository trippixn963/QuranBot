"""Tests for configuration management system."""

import os
from unittest.mock import MagicMock, patch

import pytest

from src.config import BotConfig, ConfigService, ConfigurationError
from src.config.bot_config import LogLevel, ReciterName
from src.config.exceptions import ValidationError


class TestBotConfig:
    """Test cases for BotConfig class."""

    def test_valid_configuration(self, valid_config_env):
        """Test configuration with valid environment variables."""
        with patch.dict(os.environ, valid_config_env):
            config = BotConfig()

            assert valid_config_env["DISCORD_TOKEN"] == config.DISCORD_TOKEN
            assert int(valid_config_env["GUILD_ID"]) == config.GUILD_ID
            assert (
                int(valid_config_env["TARGET_CHANNEL_ID"]) == config.TARGET_CHANNEL_ID
            )
            assert config.DEFAULT_RECITER == ReciterName.SAAD_AL_GHAMDI
            assert config.LOG_LEVEL == LogLevel.INFO

    def test_missing_required_field(self):
        """Test configuration fails with missing required fields."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(Exception):  # Pydantic ValidationError
                BotConfig()

    def test_invalid_discord_token(self, valid_config_env):
        """Test validation of Discord token."""
        invalid_tokens = [
            "",
            "short_token",
            "invalid_token_format",
        ]

        for invalid_token in invalid_tokens:
            env = valid_config_env.copy()
            env["DISCORD_TOKEN"] = invalid_token

            with patch.dict(os.environ, env):
                with pytest.raises(ValidationError):
                    BotConfig()

    def test_invalid_channel_ids(self, valid_config_env):
        """Test validation of channel IDs."""
        invalid_ids = ["-1", "0", "not_a_number"]

        for invalid_id in invalid_ids:
            env = valid_config_env.copy()
            env["TARGET_CHANNEL_ID"] = invalid_id

            with patch.dict(os.environ, env):
                with pytest.raises(Exception):  # Pydantic ValidationError
                    BotConfig()

    def test_admin_user_ids_parsing(self, valid_config_env):
        """Test parsing of admin user IDs from string."""
        test_cases = [
            ("123456789", [123456789]),
            ("123456789,987654321", [123456789, 987654321]),
            ("123456789, 987654321, 555666777", [123456789, 987654321, 555666777]),
            ("", []),
            ("   ", []),
        ]

        for input_str, expected in test_cases:
            env = valid_config_env.copy()
            env["ADMIN_USER_ID"] = input_str

            with patch.dict(os.environ, env, clear=True):
                config = BotConfig()
                assert config.admin_user_ids == expected

    def test_invalid_admin_user_ids(self, valid_config_env):
        """Test validation of invalid admin user IDs."""
        invalid_inputs = [
            "not_a_number",
            "123,not_a_number",
            "123,,456",  # Empty value
        ]

        for invalid_input in invalid_inputs:
            env = valid_config_env.copy()
            env["ADMIN_USER_ID"] = invalid_input

            with patch.dict(os.environ, env, clear=True):
                with pytest.raises(ValidationError):
                    BotConfig()

    @patch("subprocess.run")
    def test_ffmpeg_validation_success(self, mock_run, valid_config_env, tmp_path):
        """Test successful FFmpeg validation."""
        # Create a mock FFmpeg executable
        ffmpeg_path = tmp_path / "ffmpeg"
        ffmpeg_path.write_text("#!/bin/bash\necho 'ffmpeg version 4.4.0'")
        ffmpeg_path.chmod(0o755)

        # Mock subprocess.run to return success
        mock_run.return_value = MagicMock(stdout=b"ffmpeg version 4.4.0", returncode=0)

        env = valid_config_env.copy()
        env["FFMPEG_PATH"] = str(ffmpeg_path)

        with patch.dict(os.environ, env):
            config = BotConfig()
            assert ffmpeg_path == config.FFMPEG_PATH

    def test_ffmpeg_validation_not_found(self, valid_config_env):
        """Test FFmpeg validation when executable not found."""
        env = valid_config_env.copy()
        env["FFMPEG_PATH"] = "/nonexistent/ffmpeg"

        with patch.dict(os.environ, env):
            with pytest.raises(ValidationError):
                BotConfig()

    @patch("subprocess.run")
    def test_ffmpeg_validation_not_executable(
        self, mock_run, valid_config_env, tmp_path
    ):
        """Test FFmpeg validation when file is not executable."""
        # Create a non-executable file
        ffmpeg_path = tmp_path / "ffmpeg"
        ffmpeg_path.write_text("not executable")
        ffmpeg_path.chmod(0o644)  # Not executable

        env = valid_config_env.copy()
        env["FFMPEG_PATH"] = str(ffmpeg_path)

        with patch.dict(os.environ, env):
            with pytest.raises(ValidationError):
                BotConfig()

    def test_audio_folder_validation_success(self, valid_config_env, tmp_path):
        """Test successful audio folder validation."""
        # Create audio folder with MP3 files
        audio_folder = tmp_path / "audio"
        audio_folder.mkdir()
        (audio_folder / "test.mp3").write_text("fake mp3 content")

        env = valid_config_env.copy()
        env["AUDIO_FOLDER"] = str(audio_folder)

        with patch.dict(os.environ, env):
            config = BotConfig()
            assert audio_folder == config.AUDIO_FOLDER

    def test_audio_folder_validation_not_found(self, valid_config_env):
        """Test audio folder validation when folder doesn't exist."""
        env = valid_config_env.copy()
        env["AUDIO_FOLDER"] = "/nonexistent/audio"

        with patch.dict(os.environ, env):
            with pytest.raises(ValidationError):
                BotConfig()

    def test_audio_folder_validation_no_audio_files(self, valid_config_env, tmp_path):
        """Test audio folder validation when no audio files present."""
        # Create empty audio folder
        audio_folder = tmp_path / "audio"
        audio_folder.mkdir()

        env = valid_config_env.copy()
        env["AUDIO_FOLDER"] = str(audio_folder)

        with patch.dict(os.environ, env):
            with pytest.raises(ValidationError):
                BotConfig()

    def test_webhook_url_validation(self, valid_config_env):
        """Test Discord webhook URL validation."""
        valid_urls = [
            "https://discord.com/api/webhooks/123456789/abcdef123456",
            None,  # Optional field
        ]

        invalid_urls = [
            "https://example.com/webhook",
            "not_a_url",
            "http://discord.com/api/webhooks/123/abc",  # Wrong protocol
        ]

        # Test valid URLs
        for url in valid_urls:
            env = valid_config_env.copy()
            if url is not None:
                env["DISCORD_WEBHOOK_URL"] = url
            else:
                # Remove the webhook URL from environment
                env.pop("DISCORD_WEBHOOK_URL", None)

            with patch.dict(os.environ, env, clear=True):
                config = BotConfig()
                assert url == config.DISCORD_WEBHOOK_URL

        # Test invalid URLs
        for url in invalid_urls:
            env = valid_config_env.copy()
            env["DISCORD_WEBHOOK_URL"] = url

            with patch.dict(os.environ, env, clear=True):
                with pytest.raises(ValidationError):
                    BotConfig()

    def test_logging_configuration_validation(self, valid_config_env):
        """Test logging configuration validation."""
        # Test webhook logging enabled without URL
        env = valid_config_env.copy()
        env["USE_WEBHOOK_LOGGING"] = "true"
        # Remove DISCORD_WEBHOOK_URL from environment
        env.pop("DISCORD_WEBHOOK_URL", None)

        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValidationError):
                BotConfig()

        # Test webhook logging enabled with URL
        env["DISCORD_WEBHOOK_URL"] = "https://discord.com/api/webhooks/123/abc"

        with patch.dict(os.environ, env, clear=True):
            config = BotConfig()
            assert config.USE_WEBHOOK_LOGGING is True
            assert config.DISCORD_WEBHOOK_URL is not None
            assert config.DISCORD_WEBHOOK_URL is not None

    def test_channel_ids_uniqueness(self, valid_config_env):
        """Test that channel IDs are unique."""
        env = valid_config_env.copy()
        env["TARGET_CHANNEL_ID"] = "123456789"
        env["PANEL_CHANNEL_ID"] = "123456789"  # Same as target

        with patch.dict(os.environ, env):
            with pytest.raises(ValidationError):
                BotConfig()

    def test_get_reciter_audio_folder(self, valid_config_env, tmp_path):
        """Test getting reciter-specific audio folder."""
        audio_folder = tmp_path / "audio"
        audio_folder.mkdir()
        (audio_folder / "test.mp3").write_text("fake mp3 content")

        env = valid_config_env.copy()
        env["AUDIO_FOLDER"] = str(audio_folder)

        with patch.dict(os.environ, env):
            config = BotConfig()

            # Test default reciter
            default_folder = config.get_reciter_audio_folder()
            expected_path = audio_folder / config.DEFAULT_RECITER.value
            assert default_folder == expected_path

            # Test specific reciter
            specific_folder = config.get_reciter_audio_folder(ReciterName.ABDUL_BASIT)
            expected_path = audio_folder / ReciterName.ABDUL_BASIT.value
            assert specific_folder == expected_path

    def test_is_admin_user(self, valid_config_env):
        """Test admin user checking."""
        env = valid_config_env.copy()
        env["ADMIN_USER_ID"] = "123456789,987654321"
        env["DEVELOPER_ID"] = "555666777"

        with patch.dict(os.environ, env):
            config = BotConfig()

            # Test admin users
            assert config.is_admin_user(123456789) is True
            assert config.is_admin_user(987654321) is True

            # Test developer
            assert config.is_admin_user(555666777) is True

            # Test non-admin user
            assert config.is_admin_user(111222333) is False

    def test_validation_summary(self, valid_config_env, tmp_path):
        """Test configuration validation summary."""
        # Setup valid environment
        audio_folder = tmp_path / "audio"
        audio_folder.mkdir(exist_ok=True)
        (audio_folder / "test.mp3").write_text("fake mp3 content")

        reciter_folder = audio_folder / ReciterName.SAAD_AL_GHAMDI.value
        reciter_folder.mkdir()
        (reciter_folder / "001.mp3").write_text("fake mp3 content")

        ffmpeg_path = tmp_path / "ffmpeg"
        ffmpeg_path.write_text("#!/bin/bash\necho 'ffmpeg version 4.4.0'")
        ffmpeg_path.chmod(0o755)

        env = valid_config_env.copy()
        env["AUDIO_FOLDER"] = str(audio_folder)
        env["FFMPEG_PATH"] = str(ffmpeg_path)
        env["USE_WEBHOOK_LOGGING"] = "false"

        with patch.dict(os.environ, env), patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=b"ffmpeg version 4.4.0", returncode=0
            )

            config = BotConfig()
            summary = config.get_validation_summary()

            assert summary["discord_configured"] is True
            assert summary["audio_configured"] is True
            assert summary["ffmpeg_available"] is True
            assert summary["logging_configured"] is True
            assert summary["reciter_folder_exists"] is True


class TestConfigService:
    """Test cases for ConfigService class."""

    def test_singleton_behavior(self):
        """Test that ConfigService follows singleton pattern."""
        service1 = ConfigService()
        service2 = ConfigService()

        assert service1 is service2

    @patch("src.config.config_service.BotConfig")
    def test_configuration_loading(self, mock_bot_config):
        """Test configuration loading in service."""
        mock_config = MagicMock()
        mock_bot_config.return_value = mock_config

        # Clear singleton instance
        ConfigService._instance = None
        ConfigService._config = None

        service = ConfigService()

        assert service.config is mock_config
        mock_bot_config.assert_called_once()

    @patch("src.config.config_service.BotConfig")
    def test_configuration_loading_failure(self, mock_bot_config):
        """Test configuration loading failure handling."""
        mock_bot_config.side_effect = Exception("Configuration error")

        # Clear singleton instance
        ConfigService._instance = None
        ConfigService._config = None

        with pytest.raises(ConfigurationError):
            ConfigService()

    def test_config_access_methods(self, valid_config_env, tmp_path):
        """Test configuration access methods."""
        # Setup valid environment
        audio_folder = tmp_path / "audio"
        audio_folder.mkdir(exist_ok=True)
        (audio_folder / "test.mp3").write_text("fake mp3 content")

        ffmpeg_path = tmp_path / "ffmpeg"
        ffmpeg_path.write_text("#!/bin/bash\necho 'ffmpeg version 4.4.0'")
        ffmpeg_path.chmod(0o755)

        env = valid_config_env.copy()
        env["AUDIO_FOLDER"] = str(audio_folder)
        env["FFMPEG_PATH"] = str(ffmpeg_path)
        env["ADMIN_USER_ID"] = "123456789"

        with patch.dict(os.environ, env), patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=b"ffmpeg version 4.4.0", returncode=0
            )

            # Clear singleton instance
            ConfigService._instance = None
            ConfigService._config = None

            service = ConfigService()

            # Test access methods
            assert service.get_discord_token() == env["DISCORD_TOKEN"]
            assert service.get_guild_id() == int(env["GUILD_ID"])
            assert service.get_target_channel_id() == int(env["TARGET_CHANNEL_ID"])
            assert service.get_default_reciter() == ReciterName.SAAD_AL_GHAMDI
            assert service.get_ffmpeg_path() == ffmpeg_path
            assert service.get_admin_user_ids() == [123456789]
            assert service.is_admin_user(123456789) is True
            assert service.is_admin_user(999999999) is False

    def test_configuration_validation(self, valid_config_env, tmp_path):
        """Test configuration validation method."""
        # Setup valid environment
        audio_folder = tmp_path / "audio"
        audio_folder.mkdir(exist_ok=True)
        (audio_folder / "test.mp3").write_text("fake mp3 content")

        ffmpeg_path = tmp_path / "ffmpeg"
        ffmpeg_path.write_text("#!/bin/bash\necho 'ffmpeg version 4.4.0'")
        ffmpeg_path.chmod(0o755)

        env = valid_config_env.copy()
        env["AUDIO_FOLDER"] = str(audio_folder)
        env["FFMPEG_PATH"] = str(ffmpeg_path)

        with patch.dict(os.environ, env), patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=b"ffmpeg version 4.4.0", returncode=0
            )

            # Clear singleton instance
            ConfigService._instance = None
            ConfigService._config = None

            service = ConfigService()
            validation = service.validate_configuration()

            assert validation["overall_status"] is True
            assert validation["critical_issues"] == 0
            assert validation["discord_configured"] is True
            assert validation["audio_configured"] is True
            assert validation["ffmpeg_available"] is True

    def test_environment_detection(self):
        """Test environment detection methods."""
        # Clear singleton instance
        ConfigService._instance = None
        ConfigService._config = None

        # Test development environment
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            service = ConfigService()
            assert service.is_development_environment() is True
            assert service.is_production_environment() is False
            assert service.get_environment_name() == "development"

        # Test production environment (default)
        with patch.dict(os.environ, {}, clear=True):
            # Clear singleton instance again
            ConfigService._instance = None
            ConfigService._config = None

            # This will fail due to missing config, but we can test the method directly
            service = ConfigService.__new__(ConfigService)
            assert service.is_development_environment() is False
            assert service.is_production_environment() is True
            assert service.get_environment_name() == "production"


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def valid_config_env(tmp_path) -> dict[str, str]:
    """Provide valid configuration environment variables."""
    # Create temporary audio folder with files
    audio_folder = tmp_path / "audio"
    audio_folder.mkdir()
    (audio_folder / "test.mp3").write_text("fake mp3 content")

    # Create temporary FFmpeg executable
    ffmpeg_path = tmp_path / "ffmpeg"
    ffmpeg_path.write_text("#!/bin/bash\necho 'ffmpeg version 4.4.0'")
    ffmpeg_path.chmod(0o755)

    return {
        "DISCORD_TOKEN": "FAKE_TOKEN_FOR_TESTING.12345.67890-abcdef",
        "GUILD_ID": "1228455909827805308",
        "TARGET_CHANNEL_ID": "1389675580253016144",
        "PANEL_CHANNEL_ID": "1389716643512455219",
        "AUDIO_FOLDER": str(audio_folder),
        "FFMPEG_PATH": str(ffmpeg_path),
        "DEFAULT_RECITER": "Saad Al Ghamdi",
        "LOG_LEVEL": "INFO",
        "USE_WEBHOOK_LOGGING": "false",  # Disable webhook logging by default
    }


@pytest.fixture(autouse=True)
def reset_config_service():
    """Reset ConfigService singleton between tests."""
    yield
    # Reset singleton instance after each test
    ConfigService._instance = None
    ConfigService._config = None
