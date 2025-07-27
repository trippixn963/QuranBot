#!/usr/bin/env python3
# =============================================================================
# QuranBot - Simple Configuration Tests
# =============================================================================
# Simple configuration tests for QuranBot.
# =============================================================================

import os
from pathlib import Path
import tempfile
from unittest.mock import MagicMock, patch

# Create a temporary FFmpeg executable
with tempfile.TemporaryDirectory() as tmp_dir:
    ffmpeg_path = Path(tmp_dir) / "ffmpeg"
    ffmpeg_path.write_text('#!/bin/bash\necho "ffmpeg version 4.4.0"')
    ffmpeg_path.chmod(0o755)

    # Create a temporary audio folder
    audio_folder = Path(tmp_dir) / "audio"
    audio_folder.mkdir()
    (audio_folder / "test.mp3").write_text("fake mp3 content")

    # Set environment variables
    os.environ[
        "DISCORD_TOKEN"
    ] = "FAKE_TOKEN_FOR_TESTING.12345.67890-abcdef"
    os.environ["GUILD_ID"] = "1228455909827805308"
    os.environ["TARGET_CHANNEL_ID"] = "1389675580253016144"
    os.environ["FFMPEG_PATH"] = str(ffmpeg_path)
    os.environ["AUDIO_FOLDER"] = str(audio_folder)

    # Mock subprocess.run for FFmpeg validation
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=b"ffmpeg version 4.4.0", returncode=0)

        from src.config import BotConfig

        config = BotConfig()
        print("✅ Configuration loaded successfully!")
        print(f"Discord token: {config.DISCORD_TOKEN[:20]}...")
        print(f"Guild ID: {config.GUILD_ID}")
        print(f"Audio folder: {config.AUDIO_FOLDER}")
        print(f"FFmpeg path: {config.FFMPEG_PATH}")
        print(f"Default reciter: {config.DEFAULT_RECITER}")
        print(f"Admin user IDs: {config.admin_user_ids}")

        # Test ConfigService
        from src.config import ConfigService

        service = ConfigService()
        print("✅ ConfigService loaded successfully!")
        print(f"Service Discord token: {service.get_discord_token()[:20]}...")
        print(f"Service Guild ID: {service.get_guild_id()}")

        # Test validation
        validation = service.validate_configuration()
        print(f'✅ Validation result: {validation["overall_status"]}')

print("✅ All configuration tests passed!")
