# =============================================================================
# QuranBot - Modern State Service
# =============================================================================
# This module provides a modern, type-safe state management service with
# atomic operations, backup management, corruption recovery, and comprehensive
# validation using Pydantic models.
# =============================================================================

import asyncio
from datetime import UTC, datetime
import gzip
import hashlib
import json
from pathlib import Path
import uuid

import aiofiles

from src.core.di_container import DIContainer
from src.core.exceptions import StateError, ValidationError
from src.core.structured_logger import StructuredLogger
from src.data.models import (
    BackupInfo,
    BotSession,
    BotStatistics,
    PlaybackPosition,
    PlaybackState,
    StateServiceConfig,
    StateSnapshot,
    StateValidationResult,
)


class StateService:
    """
    Modern state management service with atomic operations and validation.

    This service provides comprehensive state management functionality including:
    - Atomic read/write operations to prevent corruption
    - Automatic backup creation and rotation
    - State validation and corruption recovery
    - Session tracking and statistics
    - Dependency injection integration
    - Comprehensive error handling
    """

    def __init__(
        self,
        container: DIContainer,
        config: StateServiceConfig,
        logger: StructuredLogger,
    ):
        """
        Initialize the state service.

        Args:
            container: Dependency injection container
            config: State service configuration
            logger: Structured logger
        """
        self._container = container
        self._config = config
        self._logger = logger

        # Initialize state tracking
        self._current_session: BotSession | None = None
        self._bot_statistics = BotStatistics()
        self._playback_state = PlaybackState(
            current_reciter="Saad Al Ghamdi",
            current_position=PlaybackPosition(surah_number=1),
        )

        # File paths
        self._playback_state_file = self._config.data_directory / "playback_state.json"
        self._bot_statistics_file = self._config.data_directory / "bot_statistics.json"
        self._session_file = self._config.data_directory / "current_session.json"

        # Background tasks
        self._backup_task: asyncio.Task | None = None
        self._cleanup_task: asyncio.Task | None = None

        # State locks for thread safety
        self._playback_lock = asyncio.Lock()
        self._statistics_lock = asyncio.Lock()
        self._session_lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize the state service"""
        await self._logger.info("Initializing state service")

        try:
            # Create directories
            await self._ensure_directories()

            # Load existing state
            await self._load_existing_state()

            # Start new session
            await self._start_new_session()

            # Start background tasks
            await self._start_background_tasks()

            await self._logger.info(
                "State service initialized successfully",
                {
                    "data_directory": str(self._config.data_directory),
                    "backup_enabled": self._config.enable_backups,
                    "atomic_writes": self._config.atomic_writes,
                    "session_id": (
                        self._current_session.session_id
                        if self._current_session
                        else None
                    ),
                },
            )

        except Exception as e:
            await self._logger.error(
                "Failed to initialize state service", {"error": str(e)}
            )
            raise StateError(
                "State service initialization failed",
                context={"operation": "initialization"},
                original_error=e,
            )

    async def shutdown(self) -> None:
        """Shutdown the state service"""
        await self._logger.info("Shutting down state service")

        try:
            # End current session
            if self._current_session:
                await self._end_current_session("shutdown")

            # Cancel background tasks
            tasks = [self._backup_task, self._cleanup_task]
            for task in tasks:
                if task and not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

            # Save final state
            await self._save_all_state()

            # Create final backup
            if self._config.enable_backups:
                await self._create_backup("shutdown")

            await self._logger.info("State service shutdown complete")

        except Exception as e:
            await self._logger.error(
                "Error during state service shutdown", {"error": str(e)}
            )

    # =============================================================================
    # Playback State Management
    # =============================================================================

    async def save_playback_state(
        self,
        surah_number: int,
        position_seconds: float,
        reciter: str,
        is_playing: bool = False,
        is_paused: bool = False,
        volume: float = 1.0,
    ) -> bool:
        """
        Save playback state with validation and atomic operations.

        Args:
            surah_number: Current surah number (1-114)
            position_seconds: Current position in seconds
            reciter: Current reciter name
            is_playing: Whether audio is playing
            is_paused: Whether audio is paused
            volume: Current volume (0.0-1.0)

        Returns:
            True if state saved successfully
        """
        try:
            async with self._playback_lock:
                # Create new playback state
                position = PlaybackPosition(
                    surah_number=surah_number,
                    position_seconds=position_seconds,
                    timestamp=datetime.now(UTC),
                )

                new_state = PlaybackState(
                    is_playing=is_playing,
                    is_paused=is_paused,
                    current_reciter=reciter,
                    current_position=position,
                    volume=volume,
                    last_updated=datetime.now(UTC),
                )

                # Atomic save
                success = await self._atomic_save_json(
                    self._playback_state_file, new_state.model_dump()
                )

                if success:
                    self._playback_state = new_state
                    await self._logger.debug(
                        "Playback state saved",
                        {
                            "surah": surah_number,
                            "position": f"{position_seconds:.1f}s",
                            "reciter": reciter,
                            "is_playing": is_playing,
                        },
                    )

                return success

        except ValidationError as e:
            await self._logger.error(
                "Playback state validation failed",
                {
                    "surah_number": surah_number,
                    "position_seconds": position_seconds,
                    "reciter": reciter,
                    "error": str(e),
                },
            )
            return False
        except Exception as e:
            await self._logger.error("Failed to save playback state", {"error": str(e)})
            return False

    async def load_playback_state(self) -> PlaybackState:
        """
        Load playback state with validation and corruption recovery.

        Returns:
            Current playback state
        """
        try:
            async with self._playback_lock:
                if not self._playback_state_file.exists():
                    await self._logger.info(
                        "No existing playback state, using defaults"
                    )
                    return self._playback_state

                # Load and validate state
                data = await self._atomic_load_json(self._playback_state_file)
                if data:
                    try:
                        state = PlaybackState(**data)
                        self._playback_state = state

                        await self._logger.info(
                            "Playback state loaded",
                            {
                                "surah": state.current_position.surah_number,
                                "position": f"{state.current_position.position_seconds:.1f}s",
                                "reciter": state.current_reciter,
                            },
                        )

                        return state
                    except ValidationError as e:
                        await self._logger.error(
                            "Error loading playback state",
                            {"error": str(e)},
                        )
                        return self._playback_state
                else:
                    await self._logger.warning(
                        "Failed to load playback state, using defaults"
                    )
                    return self._playback_state

        except Exception as e:
            await self._logger.error("Error loading playback state", {"error": str(e)})
            return self._playback_state

    async def get_playback_state(self) -> PlaybackState:
        """Get current playback state"""
        async with self._playback_lock:
            return self._playback_state.model_copy(deep=True)

    # =============================================================================
    # Statistics Management
    # =============================================================================

    async def update_statistics(
        self,
        commands_executed: int = 0,
        voice_connections: int = 0,
        errors_count: int = 0,
        surahs_completed: int = 0,
        reciter_used: str | None = None,
    ) -> bool:
        """
        Update bot statistics.

        Args:
            commands_executed: Number of commands executed
            voice_connections: Number of voice connections
            errors_count: Number of errors
            surahs_completed: Number of surahs completed
            reciter_used: Reciter that was used

        Returns:
            True if statistics updated successfully
        """
        try:
            async with self._statistics_lock:
                # Update statistics
                self._bot_statistics.total_commands += commands_executed
                self._bot_statistics.total_voice_connections += voice_connections
                self._bot_statistics.total_errors += errors_count
                self._bot_statistics.surahs_completed += surahs_completed

                if reciter_used:
                    self._bot_statistics.favorite_reciter = reciter_used

                # Update current session if active
                if self._current_session:
                    self._current_session.commands_executed += commands_executed
                    self._current_session.voice_connections += voice_connections
                    self._current_session.errors_count += errors_count

                # Save statistics
                success = await self._atomic_save_json(
                    self._bot_statistics_file, self._bot_statistics.model_dump()
                )

                await self._logger.debug(
                    "Statistics updated",
                    {
                        "commands": commands_executed,
                        "voice_connections": voice_connections,
                        "errors": errors_count,
                        "surahs": surahs_completed,
                    },
                )

                return success

        except Exception as e:
            await self._logger.error("Failed to update statistics", {"error": str(e)})
            return False

    async def get_statistics(self) -> BotStatistics:
        """Get current bot statistics"""
        async with self._statistics_lock:
            # Calculate derived statistics
            if self._bot_statistics.total_sessions > 0:
                self._bot_statistics.average_session_duration = (
                    self._bot_statistics.total_runtime
                    / self._bot_statistics.total_sessions
                )

            return self._bot_statistics.model_copy(deep=True)

    # =============================================================================
    # Session Management
    # =============================================================================

    async def get_current_session(self) -> BotSession | None:
        """Get current active session"""
        async with self._session_lock:
            return (
                self._current_session.model_copy(deep=True)
                if self._current_session
                else None
            )

    async def end_current_session(self, reason: str = "manual") -> BotSession | None:
        """
        End the current session.

        Args:
            reason: Reason for ending the session

        Returns:
            The ended session if successful
        """
        return await self._end_current_session(reason)

    # =============================================================================
    # Backup and Recovery
    # =============================================================================

    async def create_manual_backup(
        self, description: str | None = None
    ) -> BackupInfo | None:
        """
        Create a manual backup.

        Args:
            description: Optional backup description

        Returns:
            BackupInfo if successful
        """
        return await self._create_backup("manual", description)

    async def list_backups(self, limit: int = 10) -> list[BackupInfo]:
        """
        List available backups.

        Args:
            limit: Maximum number of backups to return

        Returns:
            List of backup information
        """
        try:
            backups = []
            backup_dir = self._config.backup_directory

            if not backup_dir.exists():
                return backups

            # Find backup files
            backup_files = list(backup_dir.glob("backup_*.json.gz"))
            backup_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

            for backup_file in backup_files[:limit]:
                try:
                    stat = backup_file.stat()
                    backup_id = backup_file.stem.replace(".json", "")

                    # Try to read backup metadata from the file
                    backup_type = "automatic"  # Default
                    description = None
                    try:
                        with gzip.open(backup_file, "rt", encoding="utf-8") as f:
                            backup_data = json.load(f)
                            # Read metadata if available
                            if "metadata" in backup_data:
                                metadata = backup_data["metadata"]
                                backup_type = metadata.get("backup_type", "automatic")
                                description = metadata.get("description")
                    except Exception:
                        # If we can't read the backup, assume it's automatic
                        pass

                    backup_info = BackupInfo(
                        backup_id=backup_id,
                        file_path=backup_file,
                        backup_type=backup_type,
                        file_size=stat.st_size,
                        created_at=datetime.fromtimestamp(stat.st_mtime, tz=UTC),
                        description=description,
                    )
                    backups.append(backup_info)

                except Exception as e:
                    await self._logger.warning(
                        "Failed to read backup file info",
                        {"file": str(backup_file), "error": str(e)},
                    )

            return backups

        except Exception as e:
            await self._logger.error("Failed to list backups", {"error": str(e)})
            return []

    async def restore_from_backup(self, backup_id: str) -> bool:
        """
        Restore state from a backup.

        Args:
            backup_id: Backup identifier

        Returns:
            True if restore successful
        """
        try:
            backup_file = self._config.backup_directory / f"{backup_id}.json.gz"

            if not backup_file.exists():
                await self._logger.error(
                    "Backup file not found",
                    {"backup_id": backup_id, "file": str(backup_file)},
                )
                return False

            # Load backup data
            with gzip.open(backup_file, "rt", encoding="utf-8") as f:
                backup_data = json.load(f)

            # Validate backup data
            snapshot = StateSnapshot(**backup_data["snapshot"])

            # Restore state
            self._playback_state = snapshot.playback_state
            self._bot_statistics = snapshot.bot_statistics

            # Save restored state
            await self._save_all_state()

            await self._logger.info(
                "State restored from backup",
                {"backup_id": backup_id, "snapshot_age_hours": snapshot.age_hours},
            )

            return True

        except Exception as e:
            await self._logger.error(
                "Failed to restore from backup",
                {"backup_id": backup_id, "error": str(e)},
            )
            return False

    async def validate_state_integrity(self) -> StateValidationResult:
        """
        Validate integrity of all state files.

        Returns:
            State validation result
        """
        try:
            errors = []
            warnings = []
            corrected_fields = {}

            # Validate playback state
            if self._playback_state_file.exists():
                try:
                    data = await self._atomic_load_json(self._playback_state_file)
                    if data is None:
                        errors.append(
                            "Playback state file corrupted: failed to load JSON"
                        )
                    else:
                        PlaybackState(**data)  # Validate structure
                except ValidationError as e:
                    errors.append(f"Playback state validation failed: {e}")
                except Exception as e:
                    errors.append(f"Playback state file corrupted: {e}")
            else:
                warnings.append("Playback state file not found")

            # Validate statistics
            if self._bot_statistics_file.exists():
                try:
                    data = await self._atomic_load_json(self._bot_statistics_file)
                    if data:
                        BotStatistics(**data)  # Validate structure
                except ValidationError as e:
                    errors.append(f"Statistics validation failed: {e}")
                except Exception as e:
                    errors.append(f"Statistics file corrupted: {e}")
            else:
                warnings.append("Statistics file not found")

            # Check current session
            if self._session_file.exists():
                try:
                    data = await self._atomic_load_json(self._session_file)
                    if data:
                        BotSession(**data)  # Validate structure
                except ValidationError as e:
                    warnings.append(f"Session validation failed: {e}")
                except Exception as e:
                    warnings.append(f"Session file corrupted: {e}")

            is_valid = len(errors) == 0

            result = StateValidationResult(
                is_valid=is_valid,
                errors=errors,
                warnings=warnings,
                corrected_fields=corrected_fields,
            )

            await self._logger.info(
                "State integrity validation completed",
                {
                    "is_valid": is_valid,
                    "errors_count": len(errors),
                    "warnings_count": len(warnings),
                },
            )

            return result

        except Exception as e:
            await self._logger.error(
                "Failed to validate state integrity", {"error": str(e)}
            )
            return StateValidationResult(
                is_valid=False, errors=[f"Validation failed: {e}"]
            )

    # =============================================================================
    # Private Methods
    # =============================================================================

    async def _ensure_directories(self) -> None:
        """Ensure all required directories exist"""
        for directory in [self._config.data_directory, self._config.backup_directory]:
            directory.mkdir(parents=True, exist_ok=True)

    async def _load_existing_state(self) -> None:
        """Load all existing state from files"""
        try:
            # Load playback state
            await self.load_playback_state()

            # Load statistics
            if self._bot_statistics_file.exists():
                data = await self._atomic_load_json(self._bot_statistics_file)
                if data:
                    try:
                        self._bot_statistics = BotStatistics(**data)
                    except ValidationError as e:
                        await self._logger.warning(
                            "Statistics validation failed, using defaults",
                            {"error": str(e)},
                        )

            await self._logger.info("Existing state loaded successfully")

        except Exception as e:
            await self._logger.warning(
                "Failed to load some existing state", {"error": str(e)}
            )

    async def _start_new_session(self) -> None:
        """Start a new bot session"""
        try:
            session_id = f"session_{datetime.now(UTC).strftime('%Y_%m_%d_%H_%M_%S')}_{uuid.uuid4().hex[:8]}"

            self._current_session = BotSession(session_id=session_id)

            # Update statistics
            self._bot_statistics.total_sessions += 1
            self._bot_statistics.last_startup = datetime.now(UTC)

            # Save session
            await self._atomic_save_json(
                self._session_file, self._current_session.model_dump()
            )

            await self._logger.info("New session started", {"session_id": session_id})

        except Exception as e:
            await self._logger.error("Failed to start new session", {"error": str(e)})

    async def _end_current_session(self, reason: str) -> BotSession | None:
        """End the current session"""
        try:
            if not self._current_session:
                return None

            async with self._session_lock:
                # Update session end time
                self._current_session.end_time = datetime.now(UTC)
                self._current_session.restart_reason = reason

                # Update total runtime
                self._current_session.total_runtime = (
                    self._current_session.duration_seconds
                )
                self._bot_statistics.total_runtime += (
                    self._current_session.total_runtime
                )
                self._bot_statistics.last_shutdown = self._current_session.end_time

                # Save final session state
                await self._atomic_save_json(
                    self._session_file, self._current_session.model_dump()
                )

                ended_session = self._current_session.model_copy(deep=True)

                await self._logger.info(
                    "Session ended",
                    {
                        "session_id": self._current_session.session_id,
                        "duration": f"{self._current_session.duration_seconds:.1f}s",
                        "reason": reason,
                        "commands": self._current_session.commands_executed,
                        "errors": self._current_session.errors_count,
                    },
                )

                self._current_session = None
                return ended_session

        except Exception as e:
            await self._logger.error("Failed to end session", {"error": str(e)})
            return None

    async def _start_background_tasks(self) -> None:
        """Start background maintenance tasks"""
        if self._config.enable_backups:
            self._backup_task = asyncio.create_task(self._backup_loop())

        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        await self._logger.info("Background tasks started")

    async def _backup_loop(self) -> None:
        """Background backup creation loop"""
        while True:
            try:
                interval_seconds = self._config.backup_interval_hours * 3600
                await asyncio.sleep(interval_seconds)

                await self._create_backup("automatic")

            except asyncio.CancelledError:
                break
            except Exception as e:
                await self._logger.error("Error in backup loop", {"error": str(e)})

    async def _cleanup_loop(self) -> None:
        """Background cleanup loop"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour

                if self._config.enable_backups:
                    await self._cleanup_old_backups()

            except asyncio.CancelledError:
                break
            except Exception as e:
                await self._logger.error("Error in cleanup loop", {"error": str(e)})

    async def _create_backup(
        self, backup_type: str, description: str | None = None
    ) -> BackupInfo | None:
        """Create a state backup"""
        try:
            backup_id = f"backup_{datetime.now(UTC).strftime('%Y_%m_%d_%H_%M_%S_%f')}"
            backup_file = self._config.backup_directory / f"{backup_id}.json.gz"

            # Create snapshot
            snapshot = StateSnapshot(
                snapshot_id=backup_id,
                playback_state=self._playback_state,
                bot_statistics=self._bot_statistics,
                current_session=self._current_session,
            )

            # Add checksum
            snapshot.checksum = self._calculate_checksum(snapshot.model_dump_json())

            # Create backup data with metadata
            backup_data = {
                "snapshot": snapshot.model_dump(),
                "metadata": {
                    "backup_type": backup_type,
                    "description": description,
                    "created_at": datetime.now(UTC).isoformat(),
                },
            }

            # Save compressed backup
            with gzip.open(backup_file, "wt", encoding="utf-8") as f:
                json.dump(backup_data, f, indent=2, default=str)

            backup_info = BackupInfo(
                backup_id=backup_id,
                file_path=backup_file,
                backup_type=backup_type,
                file_size=backup_file.stat().st_size,
                description=description,
            )

            await self._logger.debug(
                "Backup created",
                {
                    "backup_id": backup_id,
                    "type": backup_type,
                    "size": backup_info.file_size,
                },
            )

            return backup_info

        except Exception as e:
            await self._logger.error(
                "Failed to create backup", {"type": backup_type, "error": str(e)}
            )
            return None

    async def _cleanup_old_backups(self) -> None:
        """Clean up old backup files"""
        try:
            backup_files = list(self._config.backup_directory.glob("backup_*.json.gz"))
            backup_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

            # Keep only the configured number of backups
            files_to_remove = backup_files[self._config.max_backups :]

            for backup_file in files_to_remove:
                backup_file.unlink()

            if files_to_remove:
                await self._logger.info(
                    "Cleaned up old backups",
                    {
                        "removed_count": len(files_to_remove),
                        "remaining_count": len(backup_files) - len(files_to_remove),
                    },
                )

        except Exception as e:
            await self._logger.error("Failed to cleanup old backups", {"error": str(e)})

    async def _save_all_state(self) -> None:
        """Save all current state to files"""
        await asyncio.gather(
            self._atomic_save_json(
                self._playback_state_file, self._playback_state.model_dump()
            ),
            self._atomic_save_json(
                self._bot_statistics_file, self._bot_statistics.model_dump()
            ),
            return_exceptions=True,
        )

    async def _atomic_save_json(self, file_path: Path, data: dict) -> bool:
        """Atomically save JSON data to file"""
        try:
            if self._config.atomic_writes:
                # Write to temporary file first
                temp_file = file_path.with_suffix(".tmp")
                async with aiofiles.open(temp_file, "w", encoding="utf-8") as f:
                    await f.write(json.dumps(data, indent=2, default=str))

                # Atomic move
                temp_file.replace(file_path)
            else:
                # Direct write
                async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                    await f.write(json.dumps(data, indent=2, default=str))

            return True

        except Exception as e:
            await self._logger.error(
                "Failed to save JSON file", {"file": str(file_path), "error": str(e)}
            )
            return False

    async def _atomic_load_json(self, file_path: Path) -> dict | None:
        """Atomically load JSON data from file"""
        try:
            async with aiofiles.open(file_path, encoding="utf-8") as f:
                content = await f.read()
                data = json.loads(content)
                if not isinstance(data, dict):
                    await self._logger.error(
                        "JSON file contains invalid data type",
                        {
                            "file": str(file_path),
                            "expected": "dict",
                            "actual": type(data).__name__,
                        },
                    )
                    return None
                return data

        except json.JSONDecodeError as e:
            await self._logger.error(
                "JSON file is corrupted", {"file": str(file_path), "error": str(e)}
            )
            return None
        except Exception as e:
            await self._logger.error(
                "Failed to load JSON file", {"file": str(file_path), "error": str(e)}
            )
            return None

    def _calculate_checksum(self, data: str) -> str:
        """Calculate SHA256 checksum of data"""
        return hashlib.sha256(data.encode("utf-8")).hexdigest()[:16]
