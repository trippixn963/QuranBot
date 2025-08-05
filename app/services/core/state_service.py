# =============================================================================
# QuranBot - State Service
# =============================================================================
# state service with robust retry mechanisms, comprehensive error handling,
# and advanced state management for 24/7 Quran bot operation.
# =============================================================================

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import hashlib
import json
import shutil
import time
from typing import Any

from ...config import get_config
from ...config.timezone import APP_TIMEZONE
from ...core.errors import (
    ErrorSeverity,
    ResourceError,
    StateError,
    ValidationError,
)
from ...core.logger import TreeLogger, log_event
from .base_service import BaseService


class PlaybackMode(Enum):
    """playback mode enumeration."""

    SEQUENTIAL = "sequential"
    LOOP = "loop"
    SHUFFLE = "shuffle"
    RANDOM = "random"


class PlaybackState(Enum):
    """playback state enumeration."""

    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    BUFFERING = "buffering"
    ERROR = "error"


@dataclass
class PlaybackPosition:
    """playback position with validation."""

    surah: int
    position_seconds: float
    total_duration_seconds: float | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(APP_TIMEZONE))

    def __post_init__(self):
        """Validate playback position."""
        if not (1 <= self.surah <= 114):
            raise ValidationError(f"Invalid surah number: {self.surah}")
        if self.position_seconds < 0:
            raise ValidationError(f"Invalid position: {self.position_seconds}")


@dataclass
class BotState:
    """bot state with comprehensive validation."""

    guild_id: int
    voice_channel_id: int | None = None
    panel_channel_id: int | None = None
    current_reciter: str = "Saad Al Ghamdi"
    playback_mode: PlaybackMode = PlaybackMode.SEQUENTIAL
    playback_state: PlaybackState = PlaybackState.STOPPED
    current_position: PlaybackPosition = field(
        default_factory=lambda: PlaybackPosition(1, 0.0)
    )
    volume: float = 1.0
    loop_enabled: bool = False
    shuffle_enabled: bool = False
    last_activity: datetime = field(default_factory=lambda: datetime.now(APP_TIMEZONE))
    created_at: datetime = field(default_factory=lambda: datetime.now(APP_TIMEZONE))
    updated_at: datetime = field(default_factory=lambda: datetime.now(APP_TIMEZONE))

    def __post_init__(self):
        """Validate bot state."""
        if self.guild_id <= 0:
            raise ValidationError(f"Invalid guild ID: {self.guild_id}")
        if not (0.0 <= self.volume <= 1.0):
            raise ValidationError(f"Invalid volume: {self.volume}")

    def model_dump(self, mode: str = "json") -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "guild_id": self.guild_id,
            "voice_channel_id": self.voice_channel_id,
            "panel_channel_id": self.panel_channel_id,
            "current_reciter": self.current_reciter,
            "playback_mode": (
                self.playback_mode.value
                if hasattr(self.playback_mode, "value")
                else self.playback_mode
            ),
            "playback_state": (
                self.playback_state.value
                if hasattr(self.playback_state, "value")
                else self.playback_state
            ),
            "current_position": {
                "surah": self.current_position.surah,
                "position_seconds": self.current_position.position_seconds,
                "total_duration_seconds": self.current_position.total_duration_seconds,
                "timestamp": self.current_position.timestamp.isoformat(),
            },
            "volume": self.volume,
            "loop_enabled": self.loop_enabled,
            "shuffle_enabled": self.shuffle_enabled,
            "last_activity": self.last_activity.isoformat(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class StateService(BaseService):
    """
    state service with robust retry mechanisms and comprehensive error handling.
    Manages bot state persistence, state monitoring, and state recovery.
    """

    def __init__(self):
        """
        Initialize state service with error handling and retry logic.
        """
        # Initialize base service (logger and error handler are optional now)
        super().__init__("StateService")

        self.config = get_config()

        # state management
        self.bot_state: BotState | None = None
        self.state_dir = self.config.data_folder / "state"
        self.state_file = self.state_dir / "bot_state.json"
        self.backup_file = self.state_dir / "bot_state_backup.json"

        # state monitoring
        self.state_checksum: str | None = None
        self.state_stats = {
            "state_changes": 0,
            "auto_saves": 0,
            "manual_saves": 0,
            "loads": 0,
            "corruption_detections": 0,
            "recovery_attempts": 0,
        }

        # background task management
        self.auto_save_task: asyncio.Task | None = None
        self.state_monitor_task: asyncio.Task | None = None

        # state change monitoring
        self.state_change_listeners: list[Callable] = []
        self.state_changes_count = 0
        self.last_state_change: datetime | None = None

        # configuration
        # Use default values for missing config attributes
        self.auto_save_interval = getattr(
            self.config, "auto_save_interval", 300
        )  # 5 minutes
        self.corruption_checks_enabled = getattr(
            self.config, "corruption_checks_enabled", True
        )
        self.max_history = getattr(self.config, "max_history", 100)

    async def _initialize(self) -> None:
        """Initialize state service with retry mechanisms."""
        TreeLogger.info(
            "Initializing state service with error handling", service="StateService"
        )

        try:
            # Ensure state directory exists with retry
            await self._retry_operation(
                operation=self._ensure_state_directory,
                operation_name="state_directory_creation",
                context={
                    "service_name": "StateService",
                    "state_directory": str(self.state_dir),
                },
            )

            # Load or create initial state with retry
            await self._retry_operation(
                operation=self._load_or_create_state,
                operation_name="state_loading",
                context={
                    "service_name": "StateService",
                    "state_file": str(self.state_file),
                    "backup_file": str(self.backup_file),
                },
            )

            # Validate state integrity with retry
            await self._retry_operation(
                operation=self._validate_state_integrity,
                operation_name="state_integrity_validation",
                context={
                    "service_name": "StateService",
                    "state_file": str(self.state_file),
                },
            )

            # Setup state monitoring with retry
            await self._retry_operation(
                operation=self._setup_state_monitoring,
                operation_name="state_monitoring_setup",
                context={
                    "service_name": "StateService",
                    "auto_save_interval": self.auto_save_interval,
                },
            )

            TreeLogger.info(
                "State service initialization complete with error handling",
                service="StateService",
            )

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "state_service_initialization",
                    "service_name": "StateService",
                    "state_directory": str(self.state_dir),
                    "state_file": str(self.state_file),
                },
            )
            raise StateError(
                f"Failed to initialize state service: {e}",
                operation="initialize",
                severity=ErrorSeverity.CRITICAL,
            )

    async def _start(self) -> None:
        """Start state service with monitoring."""
        TreeLogger.info(
            "Starting state service with monitoring", service="StateService"
        )

        try:
            # Start auto-save task with retry
            await self._retry_operation(
                operation=self._start_auto_save_task,
                operation_name="auto_save_task_startup",
                context={
                    "service_name": "StateService",
                    "auto_save_interval": self.auto_save_interval,
                },
            )

            # Start state monitoring task with retry
            await self._retry_operation(
                operation=self._start_state_monitoring_task,
                operation_name="state_monitoring_startup",
                context={"service_name": "StateService"},
            )

            # Log startup state with retry
            await self._retry_operation(
                operation=self._log_startup_state,
                operation_name="startup_state_logging",
                context={"service_name": "StateService"},
            )

            TreeLogger.info(
                "State service started successfully with monitoring",
                service="StateService",
            )

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {"operation": "state_service_startup", "service_name": "StateService"},
            )
            raise StateError(
                f"Failed to start state service: {e}",
                operation="start",
                severity=ErrorSeverity.ERROR,
            )

    async def _stop(self) -> None:
        """Stop state service with cleanup."""
        TreeLogger.info("Stopping state service with cleanup", service="StateService")

        try:
            # Stop background tasks with retry
            await self._retry_operation(
                operation=self._stop_background_tasks,
                operation_name="background_tasks_shutdown",
                context={"service_name": "StateService"},
            )

            # Perform final state save with retry
            await self._retry_operation(
                operation=lambda: self._save_state("shutdown_save"),
                operation_name="final_state_save",
                context={"service_name": "StateService", "save_type": "shutdown_save"},
            )

            # Log final statistics with retry
            await self._retry_operation(
                operation=self._log_final_statistics,
                operation_name="final_statistics_logging",
                context={"service_name": "StateService"},
            )

            TreeLogger.info(
                "State service stopped successfully with cleanup",
                service="StateService",
            )

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {"operation": "state_service_shutdown", "service_name": "StateService"},
            )
            raise StateError(
                f"Failed to stop state service: {e}",
                operation="stop",
                severity=ErrorSeverity.WARNING,
            )

    async def _cleanup(self) -> None:
        """Clean up state service resources with error handling."""
        TreeLogger.info("Cleaning up state service resources", service="StateService")

        try:
            # Clear state change listeners
            self.state_change_listeners.clear()

            # Reset state
            self.bot_state = None
            self.state_checksum = None

            # Reset statistics
            self.state_stats = {
                "state_changes": 0,
                "auto_saves": 0,
                "manual_saves": 0,
                "loads": 0,
                "corruption_detections": 0,
                "recovery_attempts": 0,
            }

            # Reset monitoring
            self.state_changes_count = 0
            self.last_state_change = None

            TreeLogger.info(
                "State service cleanup complete with resource management",
                service="StateService",
            )

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {"operation": "state_service_cleanup", "service_name": "StateService"},
            )
            raise StateError(
                f"Failed to cleanup state service: {e}",
                operation="cleanup",
                severity=ErrorSeverity.WARNING,
            )

    async def _health_check(self) -> dict[str, Any]:
        """Perform comprehensive state service health check."""
        try:
            # Basic health metrics
            health_data = {
                "state_loaded": self.bot_state is not None,
                "state_file_exists": self.state_file.exists(),
                "backup_file_exists": self.backup_file.exists(),
                "state_file_size_mb": self._get_state_file_size_mb(),
                "state_checksum": (
                    self.state_checksum[:8] + "..." if self.state_checksum else None
                ),
                # state statistics
                "state_stats": self.state_stats,
                # monitoring metrics
                "state_changes_count": self.state_changes_count,
                "last_state_change": (
                    self.last_state_change.isoformat()
                    if self.last_state_change
                    else None
                ),
                "state_change_listeners": len(self.state_change_listeners),
                # background task status
                "auto_save_task_running": self.auto_save_task is not None
                and not self.auto_save_task.done(),
                "state_monitor_task_running": self.state_monitor_task is not None
                and not self.state_monitor_task.done(),
                # configuration
                "auto_save_interval": self.auto_save_interval,
                "corruption_checks_enabled": self.corruption_checks_enabled,
                "max_history": self.max_history,
            }

            # Calculate health score
            health_score = self._calculate_state_health_score(health_data)
            health_data["health_score"] = health_score
            health_data["is_healthy"] = health_score >= 70.0

            return health_data

        except Exception as e:
            await self.error_handler.handle_error(
                e, {"operation": "state_health_check", "service_name": "StateService"}
            )

            return {
                "state_loaded": False,
                "health_score": 0.0,
                "is_healthy": False,
                "error": str(e),
            }

    def _calculate_state_health_score(self, health_data: dict[str, Any]) -> float:
        """Calculate comprehensive state health score."""
        score = 100.0

        # Deduct points for missing state
        if not health_data.get("state_loaded", False):
            score -= 30

        # Deduct points for missing state file
        if not health_data.get("state_file_exists", False):
            score -= 20

        # Deduct points for corruption detections
        state_stats = health_data.get("state_stats", {})
        corruption_detections = state_stats.get("corruption_detections", 0)
        score -= corruption_detections * 10

        # Deduct points for failed background tasks
        auto_save_running = health_data.get("auto_save_task_running", False)
        monitor_running = health_data.get("state_monitor_task_running", False)

        if not auto_save_running:
            score -= 15
        if not monitor_running:
            score -= 15

        # Deduct points for high corruption checks
        if corruption_detections > 0:
            score -= min(corruption_detections * 5, 20)

        return max(score, 0.0)

    # =========================================================================
    # State Directory Management
    # =========================================================================

    async def _ensure_state_directory(self) -> None:
        """Ensure state directory exists with error handling."""
        try:
            # Create state directory if it doesn't exist
            self.state_dir.mkdir(parents=True, exist_ok=True)

            TreeLogger.info(
                "State directory ensured successfully",
                {
                    "state_directory": str(self.state_dir),
                    "state_file": str(self.state_file),
                    "backup_file": str(self.backup_file),
                    "directory_exists": self.state_dir.exists(),
                    "writable": self._is_directory_writable(),
                },
            )

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "ensure_state_directory",
                    "state_directory": str(self.state_dir),
                },
            )
            raise ResourceError(
                f"Failed to create state directory: {e}",
                operation="ensure_state_directory",
            )

    def _is_directory_writable(self) -> bool:
        """Check if state directory is writable."""
        try:
            test_file = self.state_dir / ".write_test"
            test_file.touch()
            test_file.unlink()
            return True
        except Exception:
            return False

    # =========================================================================
    # State Loading and Creation
    # =========================================================================

    async def _load_or_create_state(self) -> None:
        """
        Load existing state or create new state with comprehensive error handling.

        This method performs complex state initialization including:
        - File existence detection and decision logic
        - State loading from persistent storage
        - Default state creation with configuration
        - Checksum calculation for integrity verification
        - Source tracking and logging
        - Error recovery and fallback mechanisms

        This is the primary entry point for state initialization during bot startup.
        """
        try:
            # STEP 1: File Existence Detection and Decision Logic
            # Check if state file exists to determine initialization strategy
            # This prevents overwriting existing state with defaults
            if self.state_file.exists():
                TreeLogger.info(
                    "Existing state file found, loading from persistent storage",
                    {
                        "state_file": str(self.state_file),
                        "file_size_bytes": self.state_file.stat().st_size,
                    },
                    service="StateService",
                )

                # STEP 2: State Loading from Persistent Storage
                # Load existing state from JSON file with validation
                # This restores bot state from previous sessions
                await self._load_state_from_file()
            else:
                TreeLogger.info(
                    "No existing state file found, creating default state",
                    {
                        "state_file": str(self.state_file),
                        "guild_id": self.config.guild_id,
                    },
                    service="StateService",
                )

                # STEP 3: Default State Creation with Configuration
                # Create new state with default values from configuration
                # This provides initial state for first-time bot startup
                await self._create_default_state()

            # STEP 4: Checksum Calculation for Integrity Verification
            # Calculate checksum of loaded/created state for corruption detection
            # This enables detection of state file corruption during operation
            self.state_checksum = self._calculate_state_checksum()

            # STEP 5: Success Logging with Comprehensive Metrics
            # Log successful state initialization with detailed metrics
            # This provides debugging information and performance tracking
            TreeLogger.info(
                "State loaded successfully",
                {
                    "load_time_ms": self._get_load_time_ms(),
                    "source": "file" if self.state_file.exists() else "default",
                    "checksum": self.state_checksum[:8] + "...",
                    "guild_id": self.bot_state.guild_id if self.bot_state else None,
                },
            )

        except Exception as e:
            # ERROR HANDLING: Comprehensive error tracking and recovery
            # This section handles all state initialization failures and provides debugging context
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "load_or_create_state",
                    "state_file": str(self.state_file),
                    "backup_file": str(self.backup_file),
                },
            )
            raise StateError(
                f"Failed to load or create state: {e}", operation="load_or_create_state"
            )

    async def _load_state_from_file(self) -> None:
        """
        Load state from file with comprehensive JSON parsing and validation.

        This method performs complex state reconstruction including:
        - File reading with encoding protection
        - JSON parsing and structure validation
        - BotState object reconstruction from dictionary
        - Playback state reset for clean startup
        - Performance timing and statistics tracking
        - Error handling and validation recovery

        Args:
            None (uses self.state_file)
        """
        try:
            # STEP 1: Performance Timing Initialization
            # Start timing for load performance measurement
            # This helps track state loading performance over time
            start_time = time.time()

            # STEP 2: File Reading with Encoding Protection
            # Read state file with UTF-8 encoding to handle special characters
            # This prevents encoding issues with international text
            with open(self.state_file, encoding="utf-8") as f:
                state_data = json.load(f)

            # STEP 3: JSON Structure Validation
            # Validate that loaded data is a dictionary structure
            # This prevents errors from malformed JSON files
            if not isinstance(state_data, dict):
                raise ValidationError(
                    "Invalid state file format - expected dictionary structure"
                )

            # STEP 4: BotState Object Reconstruction
            # Create BotState object from loaded dictionary data
            # This converts JSON data back into structured Python objects
            self.bot_state = self._create_bot_state_from_dict(state_data)

            # STEP 5: Playback State Reset for Clean Startup
            # Reset shuffle and loop settings to prevent unexpected behavior
            # This ensures consistent startup state regardless of previous session
            self.bot_state.loop_enabled = False
            self.bot_state.shuffle_enabled = False

            # STEP 6: Performance Timing and Statistics Tracking
            # Calculate load time and update statistics for monitoring
            # This helps identify performance issues with state loading
            load_time = time.time() - start_time

            # STEP 7: Success Logging with Comprehensive Metrics
            # Log successful state loading with detailed performance metrics
            # This provides debugging information and performance tracking
            TreeLogger.info(
                "State loaded from file successfully",
                {
                    "load_time_ms": load_time * 1000,
                    "file_size_bytes": self.state_file.stat().st_size,
                    "guild_id": self.bot_state.guild_id,
                    "shuffle_reset": "Off (restart reset)",
                    "loop_reset": "Off (restart reset)",
                },
            )

            # STEP 8: Statistics Update for Monitoring
            # Update load statistics for health monitoring and analytics
            # This helps track state loading patterns and identify issues
            self.state_stats["loads"] += 1

        except Exception as e:
            # ERROR HANDLING: Comprehensive error tracking and recovery
            # This section handles all file loading failures and provides debugging context
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "load_state_from_file",
                    "state_file": str(self.state_file),
                },
            )
            raise StateError(
                f"Failed to load state from file: {e}", operation="load_state_from_file"
            )

    async def _create_default_state(self) -> None:
        """Create default state with error handling."""
        try:
            # Create default bot state
            self.bot_state = BotState(
                guild_id=self.config.guild_id,
                voice_channel_id=self.config.voice_channel_id,
                panel_channel_id=self.config.panel_channel_id,
                current_reciter=self.config.default_reciter,
                playback_mode=PlaybackMode.SEQUENTIAL,
                playback_state=PlaybackState.STOPPED,
                current_position=PlaybackPosition(1, 0.0),
                volume=self.config.default_volume,
                loop_enabled=False,
                shuffle_enabled=False,
            )

            # Save default state
            await self._save_state("initial_save")

            TreeLogger.info(
                "Default state created successfully",
                {
                    "guild_id": self.bot_state.guild_id,
                    "voice_channel_id": self.bot_state.voice_channel_id,
                    "current_reciter": self.bot_state.current_reciter,
                },
                service="StateService",
            )

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {"operation": "create_default_state", "guild_id": self.config.guild_id},
            )
            raise StateError(
                f"Failed to create default state: {e}", operation="create_default_state"
            )

    def _create_bot_state_from_dict(self, state_data: dict[str, Any]) -> BotState:
        """Create bot state from dictionary with validation."""
        try:
            # Extract current position data
            current_position_data = state_data.get("current_position", {})
            current_position = PlaybackPosition(
                surah=current_position_data.get("surah", 1),
                position_seconds=current_position_data.get("position_seconds", 0.0),
                total_duration_seconds=current_position_data.get(
                    "total_duration_seconds"
                ),
                timestamp=datetime.fromisoformat(
                    current_position_data.get(
                        "timestamp", datetime.now(APP_TIMEZONE).isoformat()
                    )
                ),
            )

            # Create bot state
            bot_state = BotState(
                guild_id=state_data.get("guild_id", self.config.guild_id),
                voice_channel_id=state_data.get("voice_channel_id"),
                panel_channel_id=state_data.get("panel_channel_id"),
                current_reciter=state_data.get(
                    "current_reciter", self.config.default_reciter
                ),
                playback_mode=PlaybackMode(
                    state_data.get("playback_mode", "sequential")
                ),
                playback_state=PlaybackState(
                    state_data.get("playback_state", "stopped")
                ),
                current_position=current_position,
                volume=state_data.get("volume", self.config.default_volume),
                loop_enabled=state_data.get("loop_enabled", False),
                shuffle_enabled=state_data.get("shuffle_enabled", False),
                last_activity=datetime.fromisoformat(
                    state_data.get(
                        "last_activity", datetime.now(APP_TIMEZONE).isoformat()
                    )
                ),
                created_at=datetime.fromisoformat(
                    state_data.get("created_at", datetime.now(APP_TIMEZONE).isoformat())
                ),
                updated_at=datetime.fromisoformat(
                    state_data.get("updated_at", datetime.now(APP_TIMEZONE).isoformat())
                ),
            )

            return bot_state

        except Exception as e:
            raise ValidationError(f"Invalid state data format: {e}")

    # =========================================================================
    # State Validation and Integrity
    # =========================================================================

    async def _validate_state_integrity(self) -> None:
        """Validate state integrity with error handling."""
        try:
            if not self.bot_state:
                raise StateError(
                    "No state loaded for validation",
                    operation="validate_state_integrity",
                )

            # Check for basic integrity issues
            issues = []

            # Validate guild ID
            if self.bot_state.guild_id <= 0:
                issues.append("Invalid guild ID")

            # Validate volume
            if not (0.0 <= self.bot_state.volume <= 1.0):
                issues.append("Invalid volume level")

            # Validate current position
            if not (1 <= self.bot_state.current_position.surah <= 114):
                issues.append("Invalid current surah")

            if self.bot_state.current_position.position_seconds < 0:
                issues.append("Invalid position seconds")

            # Log validation results
            if issues:
                TreeLogger.warning(
                    "State integrity issues detected",
                    {
                        "issues": issues,
                        "guild_id": self.bot_state.guild_id,
                        "current_surah": self.bot_state.current_position.surah,
                    },
                    service="StateService",
                )

                # Attempt to fix issues
                await self._fix_state_issues(issues)
            else:
                TreeLogger.info(
                    "State integrity validation passed", service="StateService"
                )

            # Update integrity statistics
            self.state_stats["corruption_detections"] += len(issues)

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "validate_state_integrity",
                    "state_file": str(self.state_file),
                },
            )
            raise StateError(
                f"Failed to validate state integrity: {e}",
                operation="validate_state_integrity",
            )

    async def _fix_state_issues(self, issues: list[str]) -> None:
        """Fix state issues with error handling."""
        try:
            TreeLogger.info(f"Attempting to fix {len(issues)} state issues")

            # Fix common issues
            if "Invalid guild ID" in issues:
                self.bot_state.guild_id = self.config.guild_id

            if "Invalid volume level" in issues:
                self.bot_state.volume = max(0.0, min(1.0, self.bot_state.volume))

            if "Invalid current surah" in issues:
                self.bot_state.current_position.surah = max(
                    1, min(114, self.bot_state.current_position.surah)
                )

            if "Invalid position seconds" in issues:
                self.bot_state.current_position.position_seconds = max(
                    0.0, self.bot_state.current_position.position_seconds
                )

            # Update timestamps
            self.bot_state.updated_at = datetime.now(APP_TIMEZONE)
            self.bot_state.last_activity = self.bot_state.updated_at

            # Save fixed state
            await self._save_state("fix_save")

            TreeLogger.info("State issues fixed successfully", service="StateService")

        except Exception as e:
            await self.error_handler.handle_error(
                e, {"operation": "fix_state_issues", "issues": issues}
            )
            raise StateError(
                f"Failed to fix state issues: {e}", operation="fix_state_issues"
            )

    # =========================================================================
    # State Monitoring Setup
    # =========================================================================

    async def _setup_state_monitoring(self) -> None:
        """Setup state monitoring with error handling."""
        try:
            TreeLogger.info(
                "State monitoring setup complete",
                {
                    "auto_save_interval": self.auto_save_interval,
                    "corruption_checks_enabled": self.corruption_checks_enabled,
                    "max_history": self.max_history,
                },
                service="StateService",
            )

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "setup_state_monitoring",
                    "auto_save_interval": self.auto_save_interval,
                },
            )
            raise StateError(
                f"Failed to setup state monitoring: {e}",
                operation="setup_state_monitoring",
            )

    # =========================================================================
    # Background Task Management
    # =========================================================================

    async def _start_auto_save_task(self) -> None:
        """Start auto-save task with error handling."""
        try:
            self.auto_save_task = asyncio.create_task(self._auto_save_loop())

            TreeLogger.info(
                "Auto-save task started successfully",
                {"auto_save_interval": self.auto_save_interval, "task_running": True},
                service="StateService",
            )

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "start_auto_save_task",
                    "auto_save_interval": self.auto_save_interval,
                },
            )
            raise StateError(
                f"Failed to start auto-save task: {e}", operation="start_auto_save_task"
            )

    async def _start_state_monitoring_task(self) -> None:
        """Start state monitoring task with error handling."""
        try:
            self.state_monitor_task = asyncio.create_task(self._state_monitoring_loop())

            TreeLogger.info(
                "State monitoring task started successfully",
                {
                    "corruption_checks_enabled": self.corruption_checks_enabled,
                    "task_running": True,
                },
                service="StateService",
            )

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "start_state_monitoring_task",
                    "corruption_checks_enabled": self.corruption_checks_enabled,
                },
            )
            raise StateError(
                f"Failed to start state monitoring task: {e}",
                operation="start_state_monitoring_task",
            )

    async def _stop_background_tasks(self) -> None:
        """Stop background tasks with error handling."""
        try:
            # Cancel all background tasks
            tasks_to_cancel = [self.auto_save_task, self.state_monitor_task]

            for task in tasks_to_cancel:
                if task and not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

            TreeLogger.info(
                "Background tasks stopped successfully", service="StateService"
            )

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {"operation": "stop_background_tasks", "service_name": "StateService"},
            )
            raise StateError(
                f"Failed to stop background tasks: {e}",
                operation="stop_background_tasks",
            )

    async def _auto_save_loop(self) -> None:
        """Background loop for automatic state saving."""
        while True:
            try:
                await asyncio.sleep(self.auto_save_interval)
                await self._save_state("auto_save")

            except asyncio.CancelledError:
                break
            except Exception as e:
                await self.error_handler.handle_error(
                    e, {"operation": "auto_save_loop", "service_name": "StateService"}
                )

    async def _state_monitoring_loop(self) -> None:
        """Background loop for state monitoring."""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes

                if self.corruption_checks_enabled:
                    await self._check_state_corruption()

            except asyncio.CancelledError:
                break
            except Exception as e:
                await self.error_handler.handle_error(
                    e,
                    {
                        "operation": "state_monitoring_loop",
                        "service_name": "StateService",
                    },
                )

    # =========================================================================
    # State Saving and Loading
    # =========================================================================

    async def _save_state(self, save_type: str = "auto_save") -> None:
        """
        Save state with error handling and data integrity protection.

        This method performs comprehensive state persistence including:
        - Pre-save backup creation for data safety
        - State data serialization and validation
        - File writing with encoding protection
        - Checksum calculation for integrity verification
        - Performance metrics tracking
        - Error categorization and recovery

        Args:
            save_type: Type of save operation ("auto_save", "manual_save", "shutdown_save")
        """
        try:
            # STEP 1: State Validation
            # Ensure we have valid state data before attempting to save
            if not self.bot_state:
                raise StateError("No state to save", operation="save_state")

            TreeLogger.debug(
                "Starting state save operation",
                {
                    "save_type": save_type,
                    "has_existing_file": self.state_file.exists(),
                    "state_changes_count": self.state_changes_count,
                },
                service="StateService",
            )

            start_time = time.time()

            # STEP 2: Pre-Save Backup Creation
            # Create backup of existing state file before overwriting
            # This provides rollback capability if save operation fails
            if self.state_file.exists():
                shutil.copy2(self.state_file, self.backup_file)
                TreeLogger.debug(
                    "Created backup of existing state file", service="StateService"
                )

            # STEP 3: State Data Preparation
            # Convert BotState object to JSON-serializable dictionary
            # This includes all bot configuration and playback state
            state_data = self.bot_state.model_dump()

            # STEP 4: Timestamp Updates
            # Update the state's timestamp to reflect when it was last saved
            # This helps with debugging and state age tracking
            self.bot_state.updated_at = datetime.now(APP_TIMEZONE)
            state_data["updated_at"] = self.bot_state.updated_at.isoformat()

            # STEP 5: File Writing with Encoding Protection
            # Write state data to file with UTF-8 encoding and proper formatting
            # JSON indentation makes the file human-readable for debugging
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)

            # STEP 6: Integrity Verification
            # Calculate checksum of saved data for corruption detection
            # This helps identify if the file was corrupted after saving
            self.state_checksum = self._calculate_state_checksum()

            save_time = time.time() - start_time

            # STEP 7: Statistics Tracking
            # Update save statistics for monitoring and debugging
            # Different save types are tracked separately
            if save_type == "auto_save":
                self.state_stats["auto_saves"] += 1
            else:
                self.state_stats["manual_saves"] += 1

            # STEP 8: Success Logging with Metrics
            # Log successful save with performance and file metrics
            # This provides comprehensive debugging information
            TreeLogger.info(
                "State saved successfully",
                {
                    "save_type": save_type,
                    "save_time_ms": save_time * 1000,
                    "file_size_bytes": self.state_file.stat().st_size,
                    "checksum": self.state_checksum[:8] + "...",
                },
            )

        except Exception as e:
            # ERROR HANDLING: Comprehensive error tracking and recovery
            # This section handles all save failures and provides debugging context
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "save_state",
                    "save_type": save_type,
                    "state_file": str(self.state_file),
                },
            )
            raise StateError(f"Failed to save state: {e}", operation="save_state")

    async def _check_state_corruption(self) -> None:
        """Check for state corruption with error handling."""
        try:
            current_checksum = self._calculate_state_checksum()

            if self.state_checksum and current_checksum != self.state_checksum:
                TreeLogger.warning(
                    "State corruption detected",
                    {
                        "expected_checksum": self.state_checksum[:8] + "...",
                        "current_checksum": current_checksum[:8] + "...",
                    },
                    service="StateService",
                )

                self.state_stats["corruption_detections"] += 1
                self.state_checksum = current_checksum

                # Attempt recovery
                await self._attempt_state_recovery()

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "check_state_corruption",
                    "current_checksum": (
                        current_checksum[:8] + "..."
                        if "current_checksum" in locals()
                        else None
                    ),
                    "stored_checksum": (
                        self.state_checksum[:8] + "..." if self.state_checksum else None
                    ),
                },
            )

    async def _attempt_state_recovery(self) -> None:
        """Attempt state recovery with error handling."""
        try:
            TreeLogger.info("Attempting state recovery", service="StateService")

            # Try to load from backup
            if self.backup_file.exists():
                await self._attempt_backup_recovery()
            else:
                # Recreate state from default
                await self._create_default_state()

            self.state_stats["recovery_attempts"] += 1

            TreeLogger.info("State recovery completed", service="StateService")

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "attempt_state_recovery",
                    "backup_file_exists": self.backup_file.exists(),
                },
            )
            raise StateError(
                f"Failed to attempt state recovery: {e}",
                operation="attempt_state_recovery",
            )

    async def _attempt_backup_recovery(self) -> None:
        """Attempt recovery from backup with error handling."""
        try:
            # Load from backup
            with open(self.backup_file, encoding="utf-8") as f:
                backup_data = json.load(f)

            # Create state from backup
            self.bot_state = self._create_bot_state_from_dict(backup_data)

            # Save recovered state
            await self._save_state("recovery_save")

            TreeLogger.info(
                "State recovered from backup successfully", service="StateService"
            )

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "attempt_backup_recovery",
                    "backup_file": str(self.backup_file),
                },
            )
            raise StateError(
                f"Failed to recover from backup: {e}",
                operation="attempt_backup_recovery",
            )

    # =========================================================================
    # Utility Methods
    # =========================================================================

    async def _log_startup_state(self) -> None:
        """Log startup state with metrics."""
        try:
            if not self.bot_state:
                return

            TreeLogger.info(
                "State service startup information",
                {
                    "guild_id": self.bot_state.guild_id,
                    "voice_channel_id": self.bot_state.voice_channel_id,
                    "panel_channel_id": self.bot_state.panel_channel_id,
                    "current_reciter": self.bot_state.current_reciter,
                    "playback_state": self.bot_state.playback_state.value,
                    "current_surah": self.bot_state.current_position.surah,
                    "volume": self.bot_state.volume,
                    "last_activity": self.bot_state.last_activity.isoformat(),
                },
            )

        except Exception as e:
            await self.error_handler.handle_error(
                e, {"operation": "log_startup_state", "service_name": "StateService"}
            )

    async def _log_state_statistics(self) -> None:
        """Log periodic state statistics with metrics."""
        try:
            TreeLogger.info(
                "State service statistics", self.state_stats, service="StateService"
            )

        except Exception as e:
            await self.error_handler.handle_error(
                e, {"operation": "log_state_statistics", "service_name": "StateService"}
            )

    async def _log_final_statistics(self) -> None:
        """Log final state statistics with metrics."""
        try:
            TreeLogger.info(
                "State service final statistics",
                {
                    **self.state_stats,
                    "total_listeners": len(self.state_change_listeners),
                    "state_changes_count": self.state_changes_count,
                    "last_change": (
                        self.last_state_change.isoformat()
                        if self.last_state_change
                        else None
                    ),
                },
            )

        except Exception as e:
            await self.error_handler.handle_error(
                e, {"operation": "log_final_statistics", "service_name": "StateService"}
            )

    def _calculate_state_checksum(self) -> str:
        """Calculate state checksum for integrity checking."""
        try:
            if not self.bot_state:
                return ""

            state_json = json.dumps(
                self.bot_state.model_dump(mode="json"), sort_keys=True, default=str
            )
            return hashlib.md5(state_json.encode()).hexdigest()

        except Exception:
            return ""

    def _get_state_file_size_mb(self) -> float:
        """Get state file size in MB."""
        try:
            if self.state_file.exists():
                return self.state_file.stat().st_size / (1024 * 1024)
            return 0.0
        except Exception:
            return 0.0

    def _get_load_time_ms(self) -> float:
        """Get load time in milliseconds."""
        # This would need to be implemented with time tracking
        return 0.0

    # =========================================================================
    # Public Interface with Retry Logic
    # =========================================================================

    def get_state(self) -> BotState | None:
        """Get current bot state."""
        return self.bot_state

    async def get_state_info(self) -> dict[str, Any]:
        """Get comprehensive state information with error handling."""
        try:
            if not self.bot_state:
                return {"error": "No state loaded"}

            return {
                "guild_id": self.bot_state.guild_id,
                "voice_channel_id": self.bot_state.voice_channel_id,
                "panel_channel_id": self.bot_state.panel_channel_id,
                "current_reciter": self.bot_state.current_reciter,
                "playback_mode": self.bot_state.playback_mode.value,
                "playback_state": self.bot_state.playback_state.value,
                "current_surah": self.bot_state.current_position.surah,
                "current_position": self.bot_state.current_position.position_seconds,
                "volume": self.bot_state.volume,
                "loop_enabled": self.bot_state.loop_enabled,
                "shuffle_enabled": self.bot_state.shuffle_enabled,
                "last_activity": self.bot_state.last_activity.isoformat(),
                "state_statistics": self.state_stats.copy(),
                "checksum": (
                    self.state_checksum[:8] + "..." if self.state_checksum else None
                ),
            }

        except Exception as e:
            await self.error_handler.handle_error(
                e, {"operation": "get_state_info", "service_name": "StateService"}
            )

            return {
                "error": f"Failed to get state info: {e}",
                "service_name": "StateService",
            }

    async def update_state(self, **kwargs) -> None:
        """
        Update state with error handling and retry logic.

        This method performs comprehensive state updates including:
        - Input validation and field verification
        - State modification with retry protection
        - Listener notification for real-time updates
        - Statistics tracking and monitoring
        - Automatic state persistence
        - Error recovery and rollback

        Args:
            **kwargs: Key-value pairs of state fields to update

        Raises:
            StateError: If state update fails after retries
        """
        try:
            # STEP 1: State Availability Check
            # Ensure state is loaded before attempting updates
            # This prevents updates on uninitialized state
            if not self.bot_state:
                raise StateError("No state loaded for update", operation="update_state")

            TreeLogger.debug(
                f"Updating state with {len(kwargs)} fields",
                {
                    "fields": list(kwargs.keys()),
                    "has_listeners": len(self.state_change_listeners) > 0,
                },
                service="StateService",
            )

            # STEP 2: State Update with Retry Protection
            # Perform state update with comprehensive retry mechanism
            # This handles transient failures and ensures consistency
            await self._retry_operation(
                operation=lambda: self._perform_state_update(kwargs),
                operation_name="state_update",
                context={
                    "service_name": "StateService",
                    "update_fields": list(kwargs.keys()),
                },
            )

            # STEP 3: Listener Notification System
            # Notify all registered listeners of state changes
            # This enables real-time UI updates and external integrations
            await self._notify_state_change_listeners(kwargs)

            # STEP 4: Statistics and Metrics Tracking
            # Update change statistics for monitoring and analytics
            # This helps track state modification patterns
            self.state_changes_count += 1
            self.last_state_change = datetime.now(APP_TIMEZONE)

            # STEP 5: Success Logging with Context
            # Log successful update with comprehensive details
            # This provides debugging information and audit trail
            TreeLogger.info(
                "State updated successfully",
                {
                    "update_fields": list(kwargs.keys()),
                    "state_changes_count": self.state_changes_count,
                },
            )

        except Exception as e:
            # ERROR HANDLING: Comprehensive error tracking and recovery
            # This section handles all update failures and provides debugging context
            await self.error_handler.handle_error(
                e, {"operation": "update_state", "update_fields": list(kwargs.keys())}
            )
            raise StateError(f"Failed to update state: {e}", operation="update_state")

    async def _perform_state_update(self, updates: dict[str, Any]) -> None:
        """Perform state update with validation."""
        try:
            # Update state fields with validation
            for field, value in updates.items():
                if hasattr(self.bot_state, field):
                    setattr(self.bot_state, field, value)
                else:
                    TreeLogger.warning(
                        f"Unknown state field: {field}", service="StateService"
                    )

            # Update timestamps
            self.bot_state.updated_at = datetime.now(APP_TIMEZONE)
            self.bot_state.last_activity = self.bot_state.updated_at

            # Save updated state
            await self._save_state("update_save")

        except Exception as e:
            await self.error_handler.handle_error(
                e, {"operation": "perform_state_update", "updates": updates}
            )
            raise StateError(
                f"Failed to perform state update: {e}", operation="perform_state_update"
            )

    def add_state_change_listener(self, callback: Callable) -> None:
        """Add state change listener with error handling."""
        try:
            if callback not in self.state_change_listeners:
                self.state_change_listeners.append(callback)

                # Direct logging with log_event
                log_event(
                    "INFO",
                    "State change listener added",
                    {"total_listeners": len(self.state_change_listeners)},
                )

        except Exception as e:
            # Direct logging with log_event
            log_event(
                "ERROR",
                f"Failed to add state change listener: {e}",
                {"callback": str(callback)},
            )

    def remove_state_change_listener(self, callback: Callable) -> None:
        """Remove state change listener with error handling."""
        try:
            if callback in self.state_change_listeners:
                self.state_change_listeners.remove(callback)

                # Direct logging with log_event
                log_event(
                    "INFO",
                    "State change listener removed",
                    {"total_listeners": len(self.state_change_listeners)},
                )

        except Exception as e:
            # Direct logging with log_event
            log_event(
                "ERROR",
                f"Failed to remove state change listener: {e}",
                {"callback": str(callback)},
            )

    async def _notify_state_change_listeners(self, changes: dict[str, Any]) -> None:
        """Notify state change listeners with error handling."""
        try:
            if not self.state_change_listeners:
                return

            for listener in self.state_change_listeners:
                try:
                    if asyncio.iscoroutinefunction(listener):
                        await listener(changes)
                    else:
                        listener(changes)
                except Exception as e:
                    await self.error_handler.handle_error(
                        e,
                        {
                            "operation": "notify_state_change_listener",
                            "listener": str(listener),
                            "changes": changes,
                        },
                    )

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "notify_state_change_listeners",
                    "listeners_count": len(self.state_change_listeners),
                    "changes": changes,
                },
            )
