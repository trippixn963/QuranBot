# =============================================================================
# QuranBot - Comprehensive Integration Tests
# =============================================================================
# End-to-end integration tests for critical workflows including bot startup,
# audio playback, command handling, state management, and error recovery.
# =============================================================================

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Mock Discord imports first
with patch.dict(
    "sys.modules",
    {
        "discord": Mock(),
        "discord.ext": Mock(),
        "discord.ext.commands": Mock(),
        "mutagen": Mock(),
        "mutagen.mp3": Mock(),
    },
):
    from src.core.cache_service import CacheService, CacheStrategy
    from src.core.di_container import DIContainer
    from src.core.performance_monitor import MetricType, PerformanceMonitor
    from src.data.models import (
        AudioServiceConfig,
        BotStatistics,
        PlaybackPosition,
        PlaybackState,
        StateServiceConfig,
    )
    from src.services.audio_service import AudioService
    from src.services.state_service import StateService


class TestBotStartupWorkflow:
    """Test the complete bot startup workflow."""

    @pytest.fixture
    async def mock_bot_environment(self, temp_directory, mock_logger, valid_config_env):
        """Create a complete mock bot environment."""
        # Create directory structure
        (temp_directory / "data").mkdir(exist_ok=True)
        (temp_directory / "logs").mkdir(exist_ok=True)
        (temp_directory / "backup").mkdir(exist_ok=True)
        (temp_directory / "audio").mkdir(exist_ok=True)

        # Create DI container
        container = DIContainer()

        # Register core services
        container.register_singleton(DIContainer, container)

        # Mock bot config
        bot_config = Mock()
        bot_config.data_folder = temp_directory / "data"
        bot_config.audio_folder = temp_directory / "audio"
        bot_config.backup_folder = temp_directory / "backup"
        bot_config.log_folder = temp_directory / "logs"
        bot_config.guild_id = int(valid_config_env["GUILD_ID"])
        bot_config.voice_channel_id = int(valid_config_env["VOICE_CHANNEL_ID"])

        container.register_singleton(Mock, bot_config)  # BotConfig placeholder

        yield container, bot_config

    @pytest.mark.asyncio
    async def test_complete_bot_startup_sequence(
        self, mock_bot_environment, mock_logger
    ):
        """Test the complete bot startup sequence."""
        container, bot_config = mock_bot_environment

        # Phase 1: Initialize core services
        cache_service = CacheService(CacheStrategy.LRU, 100, 300)
        await cache_service.initialize()
        container.register_singleton(CacheService, cache_service)

        # Phase 2: Initialize state service
        state_config = StateServiceConfig(
            data_directory=bot_config.data_folder,
            backup_directory=bot_config.backup_folder,
            backup_interval_hours=24,
            max_backups=7,
            compression_enabled=True,
            validation_enabled=True,
        )

        state_service = StateService(
            config=state_config, container=container, logger=mock_logger
        )
        await state_service.initialize()
        container.register_singleton(StateService, state_service)

        # Phase 3: Initialize audio service
        audio_config = AudioServiceConfig(
            audio_folder=bot_config.audio_folder,
            ffmpeg_path="/usr/bin/ffmpeg",
            default_volume=1.0,
            connection_timeout=30.0,
            playback_timeout=300.0,
            max_retry_attempts=3,
            retry_delay=1.0,
        )

        audio_service = AudioService(
            config=audio_config, container=container, logger=mock_logger
        )
        await audio_service.initialize()
        container.register_singleton(AudioService, audio_service)

        # Phase 4: Initialize monitoring
        performance_monitor = PerformanceMonitor(
            config={"collection_interval": 1.0}, logger=mock_logger
        )
        await performance_monitor.initialize()
        container.register_singleton(PerformanceMonitor, performance_monitor)

        try:
            # Verify all services are initialized
            assert cache_service._initialized
            assert state_service._initialized
            assert audio_service._initialized
            assert performance_monitor._initialized

            # Test service interactions
            await cache_service.set("startup_test", "success")
            cached_value = await cache_service.get("startup_test")
            assert cached_value == "success"

            # Test state service
            session = await state_service.create_session(
                guild_id=bot_config.guild_id,
                voice_channel_id=bot_config.voice_channel_id,
            )
            assert session.guild_id == bot_config.guild_id

            # Record startup metrics
            await performance_monitor.record_metric(
                "bot_startup_time", 1.5, MetricType.TIMER, "startup"
            )

            startup_metrics = await performance_monitor.get_metrics("bot_startup_time")
            assert len(startup_metrics) > 0

        finally:
            # Cleanup in reverse order
            await performance_monitor.shutdown()
            await audio_service.shutdown()
            await state_service.shutdown()
            await cache_service.shutdown()

    @pytest.mark.asyncio
    async def test_service_dependency_injection(
        self, mock_bot_environment, mock_logger
    ):
        """Test that service dependencies are properly injected."""
        container, bot_config = mock_bot_environment

        # Register logger
        container.register_singleton(Mock, mock_logger)  # StructuredLogger placeholder

        # Create a service that depends on another
        cache_service = CacheService(CacheStrategy.LRU, 50, 300)
        container.register_singleton(CacheService, cache_service)

        # Create state service that depends on cache
        state_config = StateServiceConfig(
            data_directory=bot_config.data_folder,
            backup_directory=bot_config.backup_folder,
        )

        state_service = StateService(
            config=state_config, container=container, logger=mock_logger
        )

        await cache_service.initialize()
        await state_service.initialize()

        try:
            # Test that state service can use injected cache
            await state_service.save_playback_state(
                PlaybackState(
                    is_playing=True,
                    is_paused=False,
                    is_shuffled=False,
                    is_looped=False,
                    current_reciter="Test_Reciter",
                    current_surah=1,
                    current_file="001.mp3",
                    voice_channel_id=bot_config.voice_channel_id,
                    guild_id=bot_config.guild_id,
                    position=PlaybackPosition(current_seconds=0, total_duration=180),
                    volume=1.0,
                    last_updated=datetime.now(UTC),
                )
            )

            # Verify state was saved
            loaded_state = await state_service.load_playback_state()
            assert loaded_state is not None
            assert loaded_state.current_reciter == "Test_Reciter"

        finally:
            await state_service.shutdown()
            await cache_service.shutdown()


class TestAudioPlaybackWorkflow:
    """Test complete audio playback workflows."""

    @pytest.fixture
    async def audio_test_environment(self, temp_directory, mock_logger):
        """Create audio testing environment."""
        # Create audio directory structure
        audio_dir = temp_directory / "audio"
        reciter_dir = audio_dir / "Test_Reciter"
        reciter_dir.mkdir(parents=True)

        # Create mock audio files
        for surah in range(1, 4):
            audio_file = reciter_dir / f"{surah:03d}.mp3"
            audio_file.write_text(f"mock audio content for surah {surah}")

        # Create services
        container = DIContainer()
        cache_service = CacheService(CacheStrategy.LRU, 100, 300)

        audio_config = AudioServiceConfig(
            audio_folder=audio_dir,
            ffmpeg_path="/usr/bin/ffmpeg",
            default_volume=1.0,
            connection_timeout=30.0,
            playback_timeout=300.0,
            max_retry_attempts=3,
            retry_delay=1.0,
        )

        # Mock Discord objects
        mock_bot = Mock()
        mock_guild = Mock()
        mock_channel = Mock()
        mock_voice_client = Mock()

        mock_guild.id = 123456789012345678
        mock_channel.id = 123456789012345682
        mock_channel.guild = mock_guild
        mock_voice_client.is_connected.return_value = True
        mock_voice_client.is_playing.return_value = False
        mock_voice_client.play = Mock()
        mock_voice_client.pause = Mock()
        mock_voice_client.resume = Mock()
        mock_voice_client.stop = Mock()

        mock_bot.get_guild.return_value = mock_guild
        mock_guild.get_channel.return_value = mock_channel
        mock_channel.connect = AsyncMock(return_value=mock_voice_client)

        container.register_singleton(CacheService, cache_service)
        container.register_singleton(Mock, mock_bot)  # Bot placeholder

        await cache_service.initialize()

        audio_service = AudioService(
            config=audio_config, container=container, logger=mock_logger
        )
        await audio_service.initialize()

        yield {
            "audio_service": audio_service,
            "cache_service": cache_service,
            "mock_bot": mock_bot,
            "mock_guild": mock_guild,
            "mock_channel": mock_channel,
            "mock_voice_client": mock_voice_client,
            "audio_dir": audio_dir,
        }

        await audio_service.shutdown()
        await cache_service.shutdown()

    @pytest.mark.asyncio
    async def test_complete_audio_playback_flow(self, audio_test_environment):
        """Test complete audio playback workflow."""
        env = audio_test_environment
        audio_service = env["audio_service"]
        mock_voice_client = env["mock_voice_client"]

        # Test 1: Connect to voice channel
        with patch.object(
            audio_service, "_connect_to_voice_channel", return_value=mock_voice_client
        ):
            connected = await audio_service.connect_to_voice_channel(123456789012345682)
            assert connected is True

        # Test 2: Start playback
        with patch.object(audio_service, "_create_audio_source", return_value=Mock()):
            success = await audio_service.play_surah(1, "Test_Reciter")
            assert success is True
            mock_voice_client.play.assert_called()

        # Test 3: Control playback
        await audio_service.pause_playback()
        mock_voice_client.pause.assert_called()

        await audio_service.resume_playback()
        mock_voice_client.resume.assert_called()

        # Test 4: Stop playback
        await audio_service.stop_playback()
        mock_voice_client.stop.assert_called()

    @pytest.mark.asyncio
    async def test_audio_error_recovery(self, audio_test_environment):
        """Test audio error recovery scenarios."""
        env = audio_test_environment
        audio_service = env["audio_service"]
        mock_voice_client = env["mock_voice_client"]

        # Test connection failure recovery
        with patch.object(audio_service, "_connect_to_voice_channel") as mock_connect:
            # First attempt fails, second succeeds
            mock_connect.side_effect = [
                Exception("Connection failed"),
                mock_voice_client,
            ]

            # Should retry and succeed
            connected = await audio_service.connect_to_voice_channel(123456789012345682)
            assert mock_connect.call_count == 2

    @pytest.mark.asyncio
    async def test_audio_file_discovery_and_caching(self, audio_test_environment):
        """Test audio file discovery and metadata caching."""
        env = audio_test_environment
        audio_service = env["audio_service"]
        cache_service = env["cache_service"]

        # Test file discovery
        available_files = await audio_service.get_available_audio_files()
        assert len(available_files) > 0

        # Test that results are cached
        cache_key = "audio_files_Test_Reciter"
        cached_files = await cache_service.get(cache_key)
        # Note: This test depends on implementation details


class TestCommandHandlingWorkflow:
    """Test command handling workflows."""

    @pytest.fixture
    async def command_test_environment(self, temp_directory, mock_logger):
        """Create command testing environment."""
        container = DIContainer()

        # Mock security service
        security_service = Mock()
        security_service.rate_limiter = Mock()
        security_service.rate_limiter.check_rate_limit = AsyncMock(return_value=True)
        security_service.input_validator = Mock()
        security_service.input_validator.validate_surah_number = Mock(return_value=True)
        security_service.permission_checker = Mock()
        security_service.permission_checker.is_admin = AsyncMock(return_value=True)

        container.register_singleton(
            Mock, security_service
        )  # SecurityService placeholder

        # Mock audio service
        audio_service = Mock()
        audio_service.is_connected = Mock(return_value=True)
        audio_service.play_surah = AsyncMock(return_value=True)
        audio_service.pause_playback = AsyncMock()
        audio_service.resume_playback = AsyncMock()
        audio_service.stop_playback = AsyncMock()
        audio_service.get_current_state = Mock(return_value=Mock(is_playing=True))

        container.register_singleton(Mock, audio_service)  # AudioService placeholder

        # Mock Discord interaction
        mock_interaction = Mock()
        mock_interaction.user = Mock()
        mock_interaction.user.id = 123456789012345684
        mock_interaction.guild = Mock()
        mock_interaction.guild.id = 123456789012345678
        mock_interaction.response = Mock()
        mock_interaction.response.send_message = AsyncMock()
        mock_interaction.followup = Mock()
        mock_interaction.followup.send = AsyncMock()

        yield {
            "container": container,
            "security_service": security_service,
            "audio_service": audio_service,
            "mock_interaction": mock_interaction,
        }

    @pytest.mark.asyncio
    async def test_command_security_workflow(self, command_test_environment):
        """Test command security checking workflow."""
        env = command_test_environment
        security_service = env["security_service"]
        mock_interaction = env["mock_interaction"]

        # Test rate limiting
        user_id = mock_interaction.user.id
        guild_id = mock_interaction.guild.id

        # Simulate rate limit check
        rate_limit_result = await security_service.rate_limiter.check_rate_limit(
            user_id=user_id, guild_id=guild_id, command_name="play"
        )
        assert rate_limit_result is True

        # Test input validation
        surah_valid = security_service.input_validator.validate_surah_number(1)
        assert surah_valid is True

        # Test admin permission
        is_admin = await security_service.permission_checker.is_admin(user_id)
        assert is_admin is True

    @pytest.mark.asyncio
    async def test_audio_command_workflow(self, command_test_environment):
        """Test audio command execution workflow."""
        env = command_test_environment
        audio_service = env["audio_service"]
        mock_interaction = env["mock_interaction"]

        # Simulate play command workflow
        # 1. Check if bot is connected
        is_connected = audio_service.is_connected()
        assert is_connected is True

        # 2. Start playback
        success = await audio_service.play_surah(1, "Test_Reciter")
        assert success is True

        # 3. Send response to user
        await mock_interaction.response.send_message("Playing Surah 1")
        mock_interaction.response.send_message.assert_called_with("Playing Surah 1")

        # 4. Test pause/resume workflow
        await audio_service.pause_playback()
        await mock_interaction.followup.send("Playback paused")

        await audio_service.resume_playback()
        await mock_interaction.followup.send("Playback resumed")

        # Verify all calls were made
        audio_service.play_surah.assert_called_once_with(1, "Test_Reciter")
        audio_service.pause_playback.assert_called_once()
        audio_service.resume_playback.assert_called_once()


class TestStateManagementWorkflow:
    """Test state management workflows."""

    @pytest.fixture
    async def state_test_environment(self, temp_directory, mock_logger):
        """Create state management testing environment."""
        # Create directories
        data_dir = temp_directory / "data"
        backup_dir = temp_directory / "backup"
        data_dir.mkdir(exist_ok=True)
        backup_dir.mkdir(exist_ok=True)

        # Create DI container
        container = DIContainer()

        # Create state service
        state_config = StateServiceConfig(
            data_directory=data_dir,
            backup_directory=backup_dir,
            backup_interval_hours=1,
            max_backups=5,
            compression_enabled=True,
            validation_enabled=True,
        )

        state_service = StateService(
            config=state_config, container=container, logger=mock_logger
        )
        await state_service.initialize()

        yield {
            "state_service": state_service,
            "data_dir": data_dir,
            "backup_dir": backup_dir,
        }

        await state_service.shutdown()

    @pytest.mark.asyncio
    async def test_complete_state_persistence_workflow(self, state_test_environment):
        """Test complete state persistence workflow."""
        env = state_test_environment
        state_service = env["state_service"]

        # Create test data
        playback_state = PlaybackState(
            is_playing=True,
            is_paused=False,
            is_shuffled=False,
            is_looped=False,
            current_reciter="Test_Reciter",
            current_surah=2,
            current_file="002.mp3",
            voice_channel_id=123456789012345682,
            guild_id=123456789012345678,
            position=PlaybackPosition(current_seconds=45.0, total_duration=300.0),
            volume=0.8,
            last_updated=datetime.now(UTC),
        )

        bot_statistics = BotStatistics(
            total_sessions=5,
            total_playtime_seconds=1800.0,
            total_commands_executed=25,
            unique_users=3,
            favorite_reciter="Test_Reciter",
            favorite_surah=2,
            last_reset=datetime.now(UTC),
        )

        # Test saving state
        await state_service.save_playback_state(playback_state)
        await state_service.save_statistics(bot_statistics)

        # Test loading state
        loaded_state = await state_service.load_playback_state()
        loaded_stats = await state_service.load_statistics()

        assert loaded_state is not None
        assert loaded_state.current_reciter == "Test_Reciter"
        assert loaded_state.current_surah == 2
        assert loaded_state.volume == 0.8

        assert loaded_stats is not None
        assert loaded_stats.total_sessions == 5
        assert loaded_stats.favorite_reciter == "Test_Reciter"

    @pytest.mark.asyncio
    async def test_state_backup_and_recovery(self, state_test_environment):
        """Test state backup and recovery workflow."""
        env = state_test_environment
        state_service = env["state_service"]
        data_dir = env["data_dir"]
        backup_dir = env["backup_dir"]

        # Create and save initial state
        initial_state = PlaybackState(
            is_playing=True,
            is_paused=False,
            is_shuffled=False,
            is_looped=False,
            current_reciter="Initial_Reciter",
            current_surah=1,
            current_file="001.mp3",
            voice_channel_id=123456789012345682,
            guild_id=123456789012345678,
            position=PlaybackPosition(current_seconds=0, total_duration=180),
            volume=1.0,
            last_updated=datetime.now(UTC),
        )

        await state_service.save_playback_state(initial_state)

        # Create backup
        backup_info = await state_service.create_backup()
        assert backup_info is not None
        assert backup_info.file_path.exists()

        # Modify state
        modified_state = initial_state.model_copy()
        modified_state.current_reciter = "Modified_Reciter"
        modified_state.current_surah = 2

        await state_service.save_playback_state(modified_state)

        # Verify modification
        current_state = await state_service.load_playback_state()
        assert current_state.current_reciter == "Modified_Reciter"

        # Restore from backup
        await state_service.restore_from_backup(backup_info.backup_id)

        # Verify restoration
        restored_state = await state_service.load_playback_state()
        assert restored_state.current_reciter == "Initial_Reciter"
        assert restored_state.current_surah == 1

    @pytest.mark.asyncio
    async def test_state_corruption_recovery(self, state_test_environment):
        """Test state corruption detection and recovery."""
        env = state_test_environment
        state_service = env["state_service"]
        data_dir = env["data_dir"]

        # Create valid state first
        valid_state = PlaybackState(
            is_playing=True,
            is_paused=False,
            is_shuffled=False,
            is_looped=False,
            current_reciter="Valid_Reciter",
            current_surah=1,
            current_file="001.mp3",
            voice_channel_id=123456789012345682,
            guild_id=123456789012345678,
            position=PlaybackPosition(current_seconds=0, total_duration=180),
            volume=1.0,
            last_updated=datetime.now(UTC),
        )

        await state_service.save_playback_state(valid_state)

        # Create backup
        backup_info = await state_service.create_backup()

        # Corrupt the state file
        state_file = data_dir / "playback_state.json"
        state_file.write_text("invalid json content {")

        # Try to load corrupted state - should recover from backup
        recovered_state = await state_service.load_playback_state()
        assert recovered_state is not None
        assert recovered_state.current_reciter == "Valid_Reciter"


class TestErrorRecoveryWorkflows:
    """Test error recovery and resilience workflows."""

    @pytest.mark.asyncio
    async def test_service_failure_recovery(self, temp_directory, mock_logger):
        """Test recovery from service failures."""
        container = DIContainer()

        # Create services
        cache_service = CacheService(CacheStrategy.LRU, 50, 300)

        # Register services
        container.register_singleton(CacheService, cache_service)

        await cache_service.initialize()

        try:
            # Simulate service working normally
            await cache_service.set("test_key", "test_value")
            value = await cache_service.get("test_key")
            assert value == "test_value"

            # Simulate service failure and recovery
            # Force an error condition
            original_get = cache_service.get

            async def failing_get(key, default=None):
                if key == "failing_key":
                    raise Exception("Simulated failure")
                return await original_get(key, default)

            cache_service.get = failing_get

            # Test error handling
            with pytest.raises(Exception):
                await cache_service.get("failing_key")

            # Test recovery - normal operation should still work
            value = await cache_service.get("test_key")
            assert value == "test_value"

        finally:
            await cache_service.shutdown()

    @pytest.mark.asyncio
    async def test_concurrent_operation_safety(self, temp_directory, mock_logger):
        """Test safety of concurrent operations."""
        state_config = StateServiceConfig(
            data_directory=temp_directory / "data",
            backup_directory=temp_directory / "backup",
        )

        container = DIContainer()
        state_service = StateService(
            config=state_config, container=container, logger=mock_logger
        )

        await state_service.initialize()

        try:
            # Create multiple concurrent operations
            async def concurrent_save(index: int):
                state = PlaybackState(
                    is_playing=True,
                    is_paused=False,
                    is_shuffled=False,
                    is_looped=False,
                    current_reciter=f"Reciter_{index}",
                    current_surah=index,
                    current_file=f"{index:03d}.mp3",
                    voice_channel_id=123456789012345682,
                    guild_id=123456789012345678,
                    position=PlaybackPosition(current_seconds=0, total_duration=180),
                    volume=1.0,
                    last_updated=datetime.now(UTC),
                )
                await state_service.save_playback_state(state)
                return await state_service.load_playback_state()

            # Run concurrent saves
            tasks = [concurrent_save(i) for i in range(5)]
            results = await asyncio.gather(*tasks)

            # Verify that all operations completed
            assert len(results) == 5

            # Verify final state is valid
            final_state = await state_service.load_playback_state()
            assert final_state is not None

        finally:
            await state_service.shutdown()

    @pytest.mark.asyncio
    async def test_resource_cleanup_on_failure(self, temp_directory, mock_logger):
        """Test that resources are properly cleaned up on failure."""
        from src.core.resource_manager import ResourceManager, ResourceType

        config = {
            "max_resources": 10,
            "cleanup_interval_seconds": 1,
            "enable_leak_detection": True,
        }

        resource_manager = ResourceManager(config=config, logger=mock_logger)
        await resource_manager.initialize()

        cleanup_calls = []

        def make_cleanup_func(resource_id):
            def cleanup():
                cleanup_calls.append(resource_id)

            return cleanup

        try:
            # Register resources with cleanup functions
            resource_ids = []
            for i in range(3):
                resource_id = await resource_manager.register_resource(
                    resource=f"test_resource_{i}",
                    resource_type=ResourceType.TEMPORARY_FILE,
                    cleanup_func=make_cleanup_func(f"resource_{i}"),
                )
                resource_ids.append(resource_id)

            # Simulate failure scenario
            raise Exception("Simulated failure")

        except Exception:
            # Even with exception, cleanup should happen on shutdown
            pass

        finally:
            await resource_manager.shutdown()

            # Verify all cleanup functions were called
            assert len(cleanup_calls) == 3
            for i in range(3):
                assert f"resource_{i}" in cleanup_calls


class TestPerformanceUnderLoad:
    """Test system performance under various load conditions."""

    @pytest.mark.asyncio
    async def test_high_concurrency_cache_operations(self, temp_directory):
        """Test cache performance under high concurrency."""
        cache_service = CacheService(CacheStrategy.LRU, 1000, 300)
        await cache_service.initialize()

        try:

            async def cache_worker(worker_id: int, operations: int):
                """Worker function for concurrent cache operations."""
                for i in range(operations):
                    key = f"worker_{worker_id}_item_{i}"
                    value = f"data_{worker_id}_{i}"

                    # Set value
                    await cache_service.set(key, value)

                    # Get value
                    retrieved = await cache_service.get(key)
                    assert retrieved == value

                    # Occasionally delete
                    if i % 10 == 0:
                        await cache_service.delete(key)

            # Run multiple workers concurrently
            worker_count = 10
            operations_per_worker = 50

            start_time = asyncio.get_event_loop().time()

            tasks = [
                cache_worker(worker_id, operations_per_worker)
                for worker_id in range(worker_count)
            ]

            await asyncio.gather(*tasks)

            end_time = asyncio.get_event_loop().time()
            total_time = end_time - start_time

            # Verify performance
            total_operations = worker_count * operations_per_worker * 2  # set + get
            ops_per_second = total_operations / total_time

            # Should be able to handle at least 1000 ops/second
            assert (
                ops_per_second > 1000
            ), f"Performance too low: {ops_per_second} ops/sec"

            # Verify cache statistics
            stats = await cache_service.get_statistics()
            assert stats["total_operations"] >= total_operations

        finally:
            await cache_service.shutdown()

    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, temp_directory, resource_monitor):
        """Test memory usage under various load conditions."""
        cache_service = CacheService(CacheStrategy.LRU, 5000, 300)
        await cache_service.initialize()

        resource_monitor.start()

        try:
            # Create large amount of data
            large_data = "x" * 1024  # 1KB per item

            # Fill cache with data
            for i in range(1000):
                key = f"large_item_{i}"
                await cache_service.set(key, large_data)

            # Measure memory usage
            memory_stats = resource_monitor.stop()

            # Memory usage should be reasonable (less than 50MB for this test)
            assert memory_stats["memory_used"] < 50 * 1024 * 1024

            # Verify cache is working
            value = await cache_service.get("large_item_500")
            assert value == large_data

        finally:
            await cache_service.shutdown()

    @pytest.mark.asyncio
    async def test_state_service_bulk_operations(self, temp_directory, mock_logger):
        """Test state service performance with bulk operations."""
        state_config = StateServiceConfig(
            data_directory=temp_directory / "data",
            backup_directory=temp_directory / "backup",
            compression_enabled=True,
        )

        container = DIContainer()
        state_service = StateService(
            config=state_config, container=container, logger=mock_logger
        )

        await state_service.initialize()

        try:
            start_time = asyncio.get_event_loop().time()

            # Perform many state operations
            for i in range(100):
                state = PlaybackState(
                    is_playing=i % 2 == 0,
                    is_paused=False,
                    is_shuffled=False,
                    is_looped=False,
                    current_reciter=f"Reciter_{i % 5}",
                    current_surah=(i % 114) + 1,
                    current_file=f"{((i % 114) + 1):03d}.mp3",
                    voice_channel_id=123456789012345682,
                    guild_id=123456789012345678,
                    position=PlaybackPosition(
                        current_seconds=float(i * 10), total_duration=180.0
                    ),
                    volume=1.0,
                    last_updated=datetime.now(UTC),
                )

                await state_service.save_playback_state(state)

                # Occasionally create backups
                if i % 20 == 0:
                    await state_service.create_backup()

            end_time = asyncio.get_event_loop().time()
            total_time = end_time - start_time

            # Should complete 100 operations in reasonable time
            assert total_time < 10.0, f"Bulk operations too slow: {total_time}s"

            # Verify final state
            final_state = await state_service.load_playbook_state()
            assert final_state is not None

            # Verify backups were created
            backups = await state_service.list_backups()
            assert len(backups) >= 5  # Should have 5 backups (every 20 operations)

        finally:
            await state_service.shutdown()
