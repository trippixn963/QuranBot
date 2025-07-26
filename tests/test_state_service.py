# =============================================================================
# QuranBot - State Service Tests
# =============================================================================
# Comprehensive tests for the modern StateService including atomic operations,
# backup management, corruption recovery, and state validation.
# =============================================================================

import asyncio
import json
from pathlib import Path
import tempfile
from unittest.mock import AsyncMock, Mock

import pytest

from src.core.di_container import DIContainer
from src.core.exceptions import StateError
from src.core.structured_logger import StructuredLogger
from src.data.models import BackupInfo, StateServiceConfig
from src.services.state_service import StateService

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
async def mock_logger():
    """Create a mock structured logger"""
    logger = Mock(spec=StructuredLogger)
    logger.info = AsyncMock()
    logger.warning = AsyncMock()
    logger.error = AsyncMock()
    logger.debug = AsyncMock()
    return logger


@pytest.fixture
def mock_container():
    """Create a mock DI container"""
    container = Mock(spec=DIContainer)
    return container


@pytest.fixture
def temp_directories():
    """Create temporary directories for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        data_dir = temp_path / "data"
        backup_dir = temp_path / "backup"
        data_dir.mkdir()
        backup_dir.mkdir()
        yield data_dir, backup_dir


@pytest.fixture
def state_config(temp_directories):
    """Create test state service configuration"""
    data_dir, backup_dir = temp_directories
    return StateServiceConfig(
        data_directory=data_dir,
        backup_directory=backup_dir,
        enable_backups=True,
        backup_interval_minutes=1,  # Fast for testing
        max_backups=5,
        atomic_writes=True,
        auto_recovery=True,
    )


@pytest.fixture
async def state_service(mock_container, state_config, mock_logger):
    """Create StateService instance for testing"""
    service = StateService(
        container=mock_container, config=state_config, logger=mock_logger
    )
    return service


class TestStateServiceInitialization:
    """Test StateService initialization and shutdown"""

    @pytest.mark.asyncio
    async def test_successful_initialization(self, state_service, mock_logger):
        """Test successful service initialization"""
        await state_service.initialize()

        # Verify logging
        mock_logger.info.assert_any_call("Initializing state service")
        mock_logger.info.assert_any_call(
            "State service initialized successfully",
            {
                "data_directory": str(state_service._config.data_directory),
                "backup_enabled": True,
                "atomic_writes": True,
                "session_id": state_service._current_session.session_id,
            },
        )

        # Verify session was started
        assert state_service._current_session is not None
        assert state_service._current_session.is_active

    @pytest.mark.asyncio
    async def test_shutdown(self, state_service, mock_logger):
        """Test service shutdown"""
        await state_service.initialize()
        session_id = state_service._current_session.session_id

        await state_service.shutdown()

        # Verify session was ended
        assert state_service._current_session is None

        # Verify logging
        mock_logger.info.assert_any_call("Shutting down state service")
        mock_logger.info.assert_any_call("State service shutdown complete")

    @pytest.mark.asyncio
    async def test_initialization_error_handling(self, mock_container, mock_logger):
        """Test initialization error handling"""
        # Create config with invalid directory
        config = StateServiceConfig(
            data_directory=Path("/invalid/path/that/does/not/exist"),
            backup_directory=Path("/invalid/backup/path"),
        )

        service = StateService(
            container=mock_container, config=config, logger=mock_logger
        )

        with pytest.raises(StateError) as exc_info:
            await service.initialize()

        assert "State service initialization failed" in str(exc_info.value)


class TestPlaybackStateManagement:
    """Test playback state operations"""

    @pytest.mark.asyncio
    async def test_save_playback_state(self, state_service):
        """Test saving playback state"""
        await state_service.initialize()

        success = await state_service.save_playback_state(
            surah_number=1,
            position_seconds=45.5,
            reciter="Test Reciter",
            is_playing=True,
            volume=0.8,
        )

        assert success is True

        # Verify state was saved
        state = await state_service.get_playback_state()
        assert state.current_position.surah_number == 1
        assert state.current_position.position_seconds == 45.5
        assert state.current_reciter == "Test Reciter"
        assert state.is_playing is True
        assert state.volume == 0.8

    @pytest.mark.asyncio
    async def test_save_invalid_playback_state(self, state_service):
        """Test saving invalid playback state"""
        await state_service.initialize()

        # Test with both playing and paused (should fail validation)
        success = await state_service.save_playback_state(
            surah_number=1,
            position_seconds=0.0,
            reciter="Test Reciter",
            is_playing=True,
            is_paused=True,  # This should cause validation to fail
        )

        assert success is False

    @pytest.mark.asyncio
    async def test_load_playback_state_file_not_exists(self, state_service):
        """Test loading playback state when file doesn't exist"""
        await state_service.initialize()

        state = await state_service.load_playback_state()

        # Should return default state
        assert state.current_position.surah_number == 1
        assert state.current_position.position_seconds == 0.0
        assert state.current_reciter == "Saad Al Ghamdi"
        assert state.is_playing is False

    @pytest.mark.asyncio
    async def test_load_corrupted_playback_state(self, state_service, state_config):
        """Test loading corrupted playback state file"""
        await state_service.initialize()

        # Create corrupted file
        corrupted_data = {"invalid": "data", "structure": "bad"}
        with open(state_config.data_directory / "playback_state.json", "w") as f:
            json.dump(corrupted_data, f)

        state = await state_service.load_playback_state()

        # Should return default state when corruption detected
        assert state.current_reciter == "Saad Al Ghamdi"

    @pytest.mark.asyncio
    async def test_playback_state_persistence(self, state_service):
        """Test that playback state persists across loads"""
        await state_service.initialize()

        # Save state
        await state_service.save_playback_state(
            surah_number=5,
            position_seconds=120.0,
            reciter="Test Reciter 2",
            is_playing=False,
            volume=0.6,
        )

        # Load state
        loaded_state = await state_service.load_playback_state()

        assert loaded_state.current_position.surah_number == 5
        assert loaded_state.current_position.position_seconds == 120.0
        assert loaded_state.current_reciter == "Test Reciter 2"
        assert loaded_state.volume == 0.6


class TestStatisticsManagement:
    """Test statistics operations"""

    @pytest.mark.asyncio
    async def test_update_statistics(self, state_service):
        """Test updating bot statistics"""
        await state_service.initialize()

        success = await state_service.update_statistics(
            commands_executed=5,
            voice_connections=2,
            errors_count=1,
            surahs_completed=3,
            reciter_used="Test Reciter",
        )

        assert success is True

        stats = await state_service.get_statistics()
        assert stats.total_commands == 5
        assert stats.total_voice_connections == 2
        assert stats.total_errors == 1
        assert stats.surahs_completed == 3
        assert stats.favorite_reciter == "Test Reciter"

    @pytest.mark.asyncio
    async def test_statistics_accumulation(self, state_service):
        """Test that statistics accumulate correctly"""
        await state_service.initialize()

        # First update
        await state_service.update_statistics(commands_executed=3, surahs_completed=1)

        # Second update
        await state_service.update_statistics(commands_executed=2, surahs_completed=2)

        stats = await state_service.get_statistics()
        assert stats.total_commands == 5
        assert stats.surahs_completed == 3

    @pytest.mark.asyncio
    async def test_session_statistics_integration(self, state_service):
        """Test that session statistics are updated with bot statistics"""
        await state_service.initialize()

        await state_service.update_statistics(
            commands_executed=3, voice_connections=1, errors_count=1
        )

        session = await state_service.get_current_session()
        assert session.commands_executed == 3
        assert session.voice_connections == 1
        assert session.errors_count == 1


class TestSessionManagement:
    """Test session management operations"""

    @pytest.mark.asyncio
    async def test_session_lifecycle(self, state_service):
        """Test complete session lifecycle"""
        await state_service.initialize()

        # Verify session was started
        session = await state_service.get_current_session()
        assert session is not None
        assert session.is_active
        session_id = session.session_id

        # End session
        ended_session = await state_service.end_current_session("test_end")

        assert ended_session is not None
        assert ended_session.session_id == session_id
        assert not ended_session.is_active
        assert ended_session.restart_reason == "test_end"

        # Verify current session is None
        current_session = await state_service.get_current_session()
        assert current_session is None

    @pytest.mark.asyncio
    async def test_session_duration_calculation(self, state_service):
        """Test session duration calculation"""
        await state_service.initialize()

        session = await state_service.get_current_session()
        start_time = session.start_time

        # Wait a bit
        await asyncio.sleep(0.1)

        # End session
        ended_session = await state_service.end_current_session("test")

        assert ended_session.duration_seconds > 0
        assert ended_session.total_runtime > 0
        assert ended_session.end_time > start_time


class TestBackupAndRecovery:
    """Test backup and recovery operations"""

    @pytest.mark.asyncio
    async def test_create_manual_backup(self, state_service):
        """Test creating manual backup"""
        await state_service.initialize()

        # Set some state
        await state_service.save_playback_state(
            surah_number=2, position_seconds=30.0, reciter="Backup Test Reciter"
        )

        backup_info = await state_service.create_manual_backup("Test backup")

        assert backup_info is not None
        assert backup_info.backup_type == "manual"
        assert backup_info.description == "Test backup"
        assert backup_info.file_path.exists()

    @pytest.mark.asyncio
    async def test_list_backups(self, state_service):
        """Test listing backups"""
        await state_service.initialize()

        # Get initial backup count (in case automatic backup ran)
        initial_backups = await state_service.list_backups()
        initial_count = len(initial_backups)

        # Create a few manual backups with some delay to ensure different timestamps
        backup1 = await state_service.create_manual_backup("Backup 1")
        await asyncio.sleep(0.1)  # Small delay to ensure different timestamps
        backup2 = await state_service.create_manual_backup("Backup 2")

        # Verify backups were created
        assert backup1 is not None, "First backup should be created successfully"
        assert backup2 is not None, "Second backup should be created successfully"

        backups = await state_service.list_backups()

        # Should have at least the 2 we created plus any initial ones
        assert (
            len(backups) >= initial_count + 2
        ), f"Expected at least {initial_count + 2} backups, got {len(backups)}"
        assert all(isinstance(backup, BackupInfo) for backup in backups)

    @pytest.mark.asyncio
    async def test_restore_from_backup(self, state_service):
        """Test restoring from backup"""
        await state_service.initialize()

        # Set initial state
        await state_service.save_playback_state(
            surah_number=3, position_seconds=60.0, reciter="Original Reciter"
        )

        # Create backup
        backup_info = await state_service.create_manual_backup("Test restore")

        # Change state
        await state_service.save_playback_state(
            surah_number=5, position_seconds=120.0, reciter="Changed Reciter"
        )

        # Restore from backup
        success = await state_service.restore_from_backup(backup_info.backup_id)
        assert success is True

        # Verify restored state
        state = await state_service.get_playback_state()
        assert state.current_position.surah_number == 3
        assert state.current_position.position_seconds == 60.0
        assert state.current_reciter == "Original Reciter"

    @pytest.mark.asyncio
    async def test_restore_from_nonexistent_backup(self, state_service):
        """Test restoring from non-existent backup"""
        await state_service.initialize()

        success = await state_service.restore_from_backup("nonexistent_backup")
        assert success is False


class TestStateValidation:
    """Test state validation and integrity checking"""

    @pytest.mark.asyncio
    async def test_validate_healthy_state(self, state_service):
        """Test validation of healthy state"""
        await state_service.initialize()

        # Save valid state
        await state_service.save_playback_state(
            surah_number=1, position_seconds=0.0, reciter="Test Reciter"
        )

        result = await state_service.validate_state_integrity()

        assert result.is_valid
        assert len(result.errors) == 0
        assert not result.has_errors

    @pytest.mark.asyncio
    async def test_validate_corrupted_state(self, state_service, state_config):
        """Test validation of corrupted state"""
        await state_service.initialize()

        # Create corrupted playback state file
        corrupted_data = {"bad": "data"}
        with open(state_config.data_directory / "playback_state.json", "w") as f:
            json.dump(corrupted_data, f)

        result = await state_service.validate_state_integrity()

        assert not result.is_valid
        assert result.has_errors
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_validate_missing_files(self, state_service, state_config):
        """Test validation with missing files"""
        await state_service.initialize()

        # Remove state files
        for file in state_config.data_directory.glob("*.json"):
            file.unlink()

        result = await state_service.validate_state_integrity()

        # Missing files should generate warnings, not errors
        assert result.has_warnings
        assert "not found" in " ".join(result.warnings)


class TestAtomicOperations:
    """Test atomic file operations"""

    @pytest.mark.asyncio
    async def test_atomic_save_success(self, state_service):
        """Test successful atomic save operation"""
        await state_service.initialize()

        test_data = {"test": "data", "number": 42}
        test_file = state_service._config.data_directory / "test_atomic.json"

        success = await state_service._atomic_save_json(test_file, test_data)

        assert success is True
        assert test_file.exists()

        # Verify content
        with open(test_file) as f:
            loaded_data = json.load(f)
        assert loaded_data == test_data

    @pytest.mark.asyncio
    async def test_atomic_load_success(self, state_service):
        """Test successful atomic load operation"""
        await state_service.initialize()

        test_data = {"test": "data", "value": 123}
        test_file = state_service._config.data_directory / "test_load.json"

        # Save data first
        with open(test_file, "w") as f:
            json.dump(test_data, f)

        loaded_data = await state_service._atomic_load_json(test_file)

        assert loaded_data == test_data

    @pytest.mark.asyncio
    async def test_atomic_load_nonexistent_file(self, state_service):
        """Test atomic load of non-existent file"""
        await state_service.initialize()

        nonexistent_file = state_service._config.data_directory / "nonexistent.json"
        loaded_data = await state_service._atomic_load_json(nonexistent_file)

        assert loaded_data is None


class TestBackgroundTasks:
    """Test background task operations"""

    @pytest.mark.asyncio
    async def test_background_tasks_start(self, state_service):
        """Test that background tasks start correctly"""
        await state_service.initialize()

        # Verify backup task started (if backups enabled)
        if state_service._config.enable_backups:
            assert state_service._backup_task is not None
            assert not state_service._backup_task.done()

        # Verify cleanup task started
        assert state_service._cleanup_task is not None
        assert not state_service._cleanup_task.done()

    @pytest.mark.asyncio
    async def test_background_tasks_cleanup(self, state_service):
        """Test background task cleanup on shutdown"""
        await state_service.initialize()

        backup_task = state_service._backup_task
        cleanup_task = state_service._cleanup_task

        await state_service.shutdown()

        # Verify tasks were cancelled
        if backup_task:
            assert backup_task.cancelled() or backup_task.done()
        if cleanup_task:
            assert cleanup_task.cancelled() or cleanup_task.done()


class TestErrorHandling:
    """Test error handling scenarios"""

    @pytest.mark.asyncio
    async def test_save_state_with_permission_error(self, state_service):
        """Test handling of permission errors during save"""
        await state_service.initialize()

        # Make data directory read-only
        state_service._config.data_directory.chmod(0o444)

        try:
            success = await state_service.save_playback_state(
                surah_number=1, position_seconds=0.0, reciter="Test"
            )

            assert success is False
        finally:
            # Restore permissions for cleanup
            state_service._config.data_directory.chmod(0o755)

    @pytest.mark.asyncio
    async def test_backup_creation_error_handling(self, state_service):
        """Test backup creation error handling"""
        await state_service.initialize()

        # Make backup directory read-only
        state_service._config.backup_directory.chmod(0o444)

        try:
            backup_info = await state_service.create_manual_backup("Test")
            assert backup_info is None
        finally:
            # Restore permissions
            state_service._config.backup_directory.chmod(0o755)


class TestConfigurationOptions:
    """Test different configuration options"""

    @pytest.mark.asyncio
    async def test_atomic_writes_disabled(
        self, mock_container, mock_logger, temp_directories
    ):
        """Test operation with atomic writes disabled"""
        data_dir, backup_dir = temp_directories
        config = StateServiceConfig(
            data_directory=data_dir, backup_directory=backup_dir, atomic_writes=False
        )

        service = StateService(
            container=mock_container, config=config, logger=mock_logger
        )

        await service.initialize()

        success = await service.save_playback_state(
            surah_number=1, position_seconds=0.0, reciter="Test"
        )

        assert success is True

    @pytest.mark.asyncio
    async def test_backups_disabled(
        self, mock_container, mock_logger, temp_directories
    ):
        """Test operation with backups disabled"""
        data_dir, backup_dir = temp_directories
        config = StateServiceConfig(
            data_directory=data_dir, backup_directory=backup_dir, enable_backups=False
        )

        service = StateService(
            container=mock_container, config=config, logger=mock_logger
        )

        await service.initialize()

        # Verify backup task was not started
        assert service._backup_task is None


class TestIntegrationScenarios:
    """Test real-world integration scenarios"""

    @pytest.mark.asyncio
    async def test_complete_state_lifecycle(self, state_service):
        """Test complete state management lifecycle"""
        # Initialize service
        await state_service.initialize()

        # Save initial playback state
        await state_service.save_playback_state(
            surah_number=1,
            position_seconds=30.0,
            reciter="Test Reciter",
            is_playing=True,
        )

        # Update statistics
        await state_service.update_statistics(
            commands_executed=5, voice_connections=1, surahs_completed=1
        )

        # Create backup
        backup_info = await state_service.create_manual_backup("Integration test")
        assert backup_info is not None

        # Validate state
        validation_result = await state_service.validate_state_integrity()
        assert validation_result.is_valid

        # End session
        ended_session = await state_service.end_current_session("integration_test")
        assert ended_session is not None

        # Shutdown
        await state_service.shutdown()

    @pytest.mark.asyncio
    async def test_recovery_from_corruption(self, state_service, state_config):
        """Test recovery from state corruption"""
        await state_service.initialize()

        # Save valid state
        await state_service.save_playback_state(
            surah_number=2, position_seconds=45.0, reciter="Original Reciter"
        )

        # Create backup
        backup_info = await state_service.create_manual_backup("Before corruption")

        # Corrupt the state file
        with open(state_config.data_directory / "playback_state.json", "w") as f:
            f.write("invalid json content {")

        # Verify corruption is detected
        validation_result = await state_service.validate_state_integrity()
        assert not validation_result.is_valid

        # Restore from backup
        success = await state_service.restore_from_backup(backup_info.backup_id)
        assert success is True

        # Verify state is restored correctly
        restored_state = await state_service.get_playback_state()
        assert restored_state.current_position.surah_number == 2
        assert restored_state.current_reciter == "Original Reciter"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
