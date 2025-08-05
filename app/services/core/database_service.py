# =============================================================================
# QuranBot - Database Service
# =============================================================================
# database service with robust retry mechanisms, comprehensive error handling,
# and advanced data management for 24/7 Quran bot operation.
# =============================================================================

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import hashlib
from pathlib import Path
import shutil
import sqlite3
import time
from typing import Any

from ...config import get_config
from ...config.timezone import APP_TIMEZONE
from ...core.errors import (
    DatabaseError,
    ErrorSeverity,
    ResourceError,
)
from ...core.logger import TreeLogger
from .base_service import BaseService


@dataclass
class QueryStats:
    """query statistics with performance tracking."""

    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    total_query_time: float = 0.0
    average_query_time: float = 0.0
    slowest_query_time: float = 0.0
    last_query_time: datetime | None = None
    queries_by_type: dict[str, int] = field(default_factory=dict)

    def update(
        self, query_time: float, success: bool, query_type: str = "unknown"
    ) -> None:
        """Update query statistics."""
        self.total_queries += 1
        self.total_query_time += query_time

        if success:
            self.successful_queries += 1
        else:
            self.failed_queries += 1

        # Update average query time
        self.average_query_time = self.total_query_time / self.total_queries

        # Update slowest query time
        if query_time > self.slowest_query_time:
            self.slowest_query_time = query_time

        # Update last query time
        self.last_query_time = datetime.now(APP_TIMEZONE)

        # Update queries by type
        self.queries_by_type[query_type] = self.queries_by_type.get(query_type, 0) + 1


@dataclass
class BackupInfo:
    """backup information with validation."""

    backup_path: str
    backup_type: str
    file_size_mb: float
    creation_time: datetime
    checksum: str | None = None
    is_valid: bool = True
    compression_ratio: float | None = None

    def __post_init__(self):
        """Validate backup information."""
        if not Path(self.backup_path).exists() or self.file_size_mb <= 0:
            self.is_valid = False


class DatabaseService(BaseService):
    """
    database service with robust retry mechanisms and comprehensive error handling.
    Manages SQLite database operations, data integrity, and automated backups.
    """

    def __init__(self):
        """
        Initialize database service with error handling and retry logic.
        """
        # Initialize base service (logger and error handler are optional now)
        super().__init__("DatabaseService")

        self.config = get_config()

        # database connection management
        self.connection: sqlite3.Connection | None = None
        self.db_path = self.config.get_database_path()
        self.backup_dir = self.config.get_backup_folder()

        # query performance tracking
        self.query_stats = QueryStats()

        # backup management
        self.backup_stats = {
            "total_backups": 0,
            "successful_backups": 0,
            "failed_backups": 0,
            "last_backup_time": None,
            "backup_size_mb": 0.0,
            "backup_interval_hours": 6,  # Default backup interval
        }

        # data integrity monitoring
        self.integrity_stats = {
            "total_checks": 0,
            "passed_checks": 0,
            "failed_checks": 0,
            "last_integrity_check": None,
            "data_corruption_events": 0,
        }

        # Background task management
        self.backup_task: asyncio.Task | None = None
        self.integrity_task: asyncio.Task | None = None
        self.cleanup_task: asyncio.Task | None = None

    async def _initialize(self) -> None:
        """Initialize database service with retry mechanisms."""
        TreeLogger.section(
            "Initializing database service with error handling",
            service="DatabaseService",
        )

        try:
            # Ensure database directory exists with retry
            await self._retry_operation(
                operation=self._ensure_database_directory,
                operation_name="database_directory_creation",
                context={
                    "service_name": "DatabaseService",
                    "database_path": str(self.db_path),
                    "backup_folder": str(self.backup_dir),
                },
            )

            # Establish database connection with retry
            await self._retry_operation(
                operation=self._establish_connection,
                operation_name="database_connection",
                context={
                    "service_name": "DatabaseService",
                    "database_path": str(self.db_path),
                },
            )

            # Initialize database schema with retry
            await self._retry_operation(
                operation=self._initialize_schema,
                operation_name="database_schema_initialization",
                context={
                    "service_name": "DatabaseService",
                    "database_path": str(self.db_path),
                },
            )

            # Validate existing data integrity with retry
            await self._retry_operation(
                operation=self._validate_data_integrity,
                operation_name="data_integrity_validation",
                context={
                    "service_name": "DatabaseService",
                    "database_path": str(self.db_path),
                },
            )

            # Setup automatic backup system with retry
            await self._retry_operation(
                operation=self._setup_backup_system,
                operation_name="backup_system_setup",
                context={
                    "service_name": "DatabaseService",
                    "backup_folder": str(self.backup_dir),
                    "backup_interval_hours": 6,  # Default backup interval
                },
            )

            TreeLogger.success(
                "Database service initialization complete with error handling",
                service="DatabaseService",
            )

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "database_service_initialization",
                    "service_name": "DatabaseService",
                    "database_path": str(self.db_path),
                    "backup_folder": str(self.backup_dir),
                },
            )
            raise DatabaseError(
                f"Failed to initialize database service: {e}",
                operation="initialize",
                severity=ErrorSeverity.CRITICAL,
            )

    async def _start(self) -> None:
        """Start database service with monitoring."""
        TreeLogger.section(
            "Starting database service with monitoring", service="DatabaseService"
        )

        try:
            # Verify connection is still valid with retry
            await self._retry_operation(
                operation=self._verify_connection,
                operation_name="connection_verification",
                context={
                    "service_name": "DatabaseService",
                    "database_path": str(self.db_path),
                },
            )

            # Start background tasks with retry
            await self._retry_operation(
                operation=self._start_background_tasks,
                operation_name="background_tasks_startup",
                context={"service_name": "DatabaseService"},
            )

            # Log startup statistics with retry
            await self._retry_operation(
                operation=self._log_startup_statistics,
                operation_name="startup_statistics_logging",
                context={"service_name": "DatabaseService"},
            )

            TreeLogger.success(
                "Database service started successfully with monitoring",
                service="DatabaseService",
            )

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "database_service_startup",
                    "service_name": "DatabaseService",
                    "database_path": str(self.db_path),
                },
            )
            raise DatabaseError(
                f"Failed to start database service: {e}",
                operation="start",
                severity=ErrorSeverity.ERROR,
            )

    async def _stop(self) -> None:
        """Stop database service with cleanup."""
        TreeLogger.section(
            "Stopping database service with cleanup", service="DatabaseService"
        )

        try:
            # Stop background tasks with retry
            await self._retry_operation(
                operation=self._stop_background_tasks,
                operation_name="background_tasks_shutdown",
                context={"service_name": "DatabaseService"},
            )

            # Perform final backup with retry
            await self._retry_operation(
                operation=lambda: self._perform_backup("shutdown_backup"),
                operation_name="final_backup",
                context={
                    "service_name": "DatabaseService",
                    "backup_type": "shutdown_backup",
                },
            )

            # Log final statistics with retry
            await self._retry_operation(
                operation=self._log_final_statistics,
                operation_name="final_statistics_logging",
                context={"service_name": "DatabaseService"},
            )

            TreeLogger.success(
                "Database service stopped successfully with cleanup",
                service="DatabaseService",
            )

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "database_service_shutdown",
                    "service_name": "DatabaseService",
                },
            )
            raise DatabaseError(
                f"Failed to stop database service: {e}",
                operation="stop",
                severity=ErrorSeverity.WARNING,
            )

    async def _cleanup(self) -> None:
        """Clean up database service resources with error handling."""
        TreeLogger.section(
            "Cleaning up database service resources", service="DatabaseService"
        )

        try:
            # Close database connection
            if self.connection:
                self.connection.close()
                self.connection = None

            # Reset statistics
            self.query_stats = QueryStats()
            self.backup_stats = {
                "total_backups": 0,
                "successful_backups": 0,
                "failed_backups": 0,
                "last_backup_time": None,
                "backup_size_mb": 0.0,
                "backup_interval_hours": 6,  # Default backup interval
            }
            self.integrity_stats = {
                "total_checks": 0,
                "passed_checks": 0,
                "failed_checks": 0,
                "last_integrity_check": None,
                "data_corruption_events": 0,
            }

            TreeLogger.success(
                "Database service cleanup complete with resource management",
                service="DatabaseService",
            )

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "database_service_cleanup",
                    "service_name": "DatabaseService",
                },
            )
            raise DatabaseError(
                f"Failed to cleanup database service: {e}",
                operation="cleanup",
                severity=ErrorSeverity.WARNING,
            )

    async def _health_check(self) -> dict[str, Any]:
        """Perform comprehensive database service health check."""
        try:
            # Basic health metrics
            health_data = {
                "connection_active": self.connection is not None,
                "database_path": str(self.db_path),
                "database_size_mb": self._get_database_size_mb(),
                "available_disk_space_mb": self._get_available_disk_space_mb(),
                "query_success_rate": self._get_success_rate(),
                # performance metrics
                "query_stats": {
                    "total_queries": self.query_stats.total_queries,
                    "successful_queries": self.query_stats.successful_queries,
                    "failed_queries": self.query_stats.failed_queries,
                    "average_query_time": self.query_stats.average_query_time,
                    "slowest_query_time": self.query_stats.slowest_query_time,
                    "queries_by_type": self.query_stats.queries_by_type,
                },
                # backup metrics
                "backup_stats": self.backup_stats,
                # integrity metrics
                "integrity_stats": self.integrity_stats,
                # Resource usage
                "table_counts": await self._get_table_counts(),
                "wal_mode_enabled": self._is_wal_mode_enabled(),
                "connection_pool_size": 1,  # SQLite uses single connection
            }

            # Calculate health score
            health_score = self._calculate_database_health_score(health_data)
            health_data["health_score"] = health_score
            health_data["is_healthy"] = health_score >= 70.0

            return health_data

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "database_health_check",
                    "service_name": "DatabaseService",
                },
            )

            return {
                "connection_active": False,
                "health_score": 0.0,
                "is_healthy": False,
                "error": str(e),
            }

    def _calculate_database_health_score(self, health_data: dict[str, Any]) -> float:
        """Calculate comprehensive database health score."""
        score = 100.0

        # Deduct points for connection issues
        if not health_data.get("connection_active", False):
            score -= 30

        # Deduct points for poor query performance
        query_stats = health_data.get("query_stats", {})
        failed_queries = query_stats.get("failed_queries", 0)
        total_queries = query_stats.get("total_queries", 0)

        if total_queries > 0:
            failure_rate = failed_queries / total_queries
            score -= failure_rate * 25

        # Deduct points for slow queries
        avg_query_time = query_stats.get("average_query_time", 0)
        if avg_query_time > 1.0:  # More than 1 second average
            score -= min((avg_query_time - 1.0) * 10, 20)

        # Deduct points for backup issues
        backup_stats = health_data.get("backup_stats", {})
        failed_backups = backup_stats.get("failed_backups", 0)
        total_backups = backup_stats.get("total_backups", 0)

        if total_backups > 0:
            backup_failure_rate = failed_backups / total_backups
            score -= backup_failure_rate * 15

        # Deduct points for integrity issues
        integrity_stats = health_data.get("integrity_stats", {})
        corruption_events = integrity_stats.get("data_corruption_events", 0)
        score -= corruption_events * 10

        # Deduct points for disk space issues
        available_space = health_data.get("available_disk_space_mb", 0)
        if available_space < 100:  # Less than 100MB available
            score -= min((100 - available_space) / 10, 15)

        return max(score, 0.0)

    # =========================================================================
    # Database Connection Management
    # =========================================================================

    async def _ensure_database_directory(self) -> None:
        """Ensure database directory exists with error handling."""
        try:
            # Create database directory if it doesn't exist
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            # Create backup directory if it doesn't exist
            self.backup_dir.mkdir(parents=True, exist_ok=True)

            TreeLogger.info(
                "Database directories ensured",
                {
                    "database_path": str(self.db_path),
                    "backup_folder": str(self.backup_dir),
                    "database_exists": self.db_path.exists(),
                    "backup_dir_exists": self.backup_dir.exists(),
                },
                service="DatabaseService",
            )

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "ensure_database_directory",
                    "database_path": str(self.db_path),
                    "backup_folder": str(self.backup_dir),
                },
            )
            raise ResourceError(
                f"Failed to create database directories: {e}",
                operation="ensure_database_directory",
            )

    async def _establish_connection(self) -> None:
        """Establish database connection with error handling."""
        try:
            start_time = time.time()

            # Create connection with timeout and retry logic
            self.connection = sqlite3.connect(
                str(self.db_path), timeout=30.0, check_same_thread=False
            )

            # Enable WAL mode for better concurrency
            self.connection.execute("PRAGMA journal_mode=WAL")

            # Set other performance optimizations
            self.connection.execute("PRAGMA synchronous=NORMAL")
            self.connection.execute("PRAGMA cache_size=10000")
            self.connection.execute("PRAGMA temp_store=MEMORY")

            connection_time = time.time() - start_time

            TreeLogger.info(
                "Database connection established successfully",
                {
                    "connection_time_ms": connection_time * 1000,
                    "database_exists": self.db_path.exists(),
                    "wal_mode": "enabled",
                    "database_size_mb": self._get_database_size_mb(),
                },
            )

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "establish_connection",
                    "database_path": str(self.db_path),
                    "database_exists": self.db_path.exists(),
                },
            )
            raise DatabaseError(
                f"Failed to establish database connection: {e}",
                operation="establish_connection",
            )

    async def _initialize_schema(self) -> None:
        """Initialize database schema with error handling."""
        try:
            start_time = time.time()

            # Create tables with schema
            tables_created = 0
            indexes_created = 0

            # User stats table
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS user_stats (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT NOT NULL,
                    total_playbacks INTEGER DEFAULT 0,
                    total_duration_seconds REAL DEFAULT 0.0,
                    favorite_reciter TEXT,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
            tables_created += 1

            # Bot state table
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS bot_state (
                    id INTEGER PRIMARY KEY,
                    guild_id INTEGER NOT NULL,
                    voice_channel_id INTEGER,
                    panel_channel_id INTEGER,
                    current_reciter TEXT DEFAULT 'Saad Al Ghamdi',
                    current_surah INTEGER DEFAULT 1,
                    playback_state TEXT DEFAULT 'stopped',
                    volume REAL DEFAULT 1.0,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
            tables_created += 1

            # Playback history table
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS playback_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    reciter TEXT NOT NULL,
                    surah_number INTEGER NOT NULL,
                    duration_seconds REAL DEFAULT 0.0,
                    completed BOOLEAN DEFAULT FALSE,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES user_stats (user_id)
                )
            """
            )
            tables_created += 1

            # System logs table
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level TEXT NOT NULL,
                    service TEXT NOT NULL,
                    message TEXT NOT NULL,
                    context TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
            tables_created += 1

            # Create indexes for performance
            self.connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_user_stats_user_id ON user_stats(user_id)"
            )
            indexes_created += 1

            self.connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_bot_state_guild_id ON bot_state(guild_id)"
            )
            indexes_created += 1

            self.connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_playback_history_user_id ON playback_history(user_id)"
            )
            indexes_created += 1

            self.connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_playback_history_timestamp ON playback_history(timestamp)"
            )
            indexes_created += 1

            self.connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp ON system_logs(timestamp)"
            )
            indexes_created += 1

            # Commit changes
            self.connection.commit()

            schema_time = time.time() - start_time

            TreeLogger.info(
                "Database schema initialized successfully",
                {
                    "tables_created": tables_created,
                    "indexes_created": indexes_created,
                    "schema_time_ms": schema_time * 1000,
                },
                service="DatabaseService",
            )

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {"operation": "initialize_schema", "database_path": str(self.db_path)},
            )
            raise DatabaseError(
                f"Failed to initialize database schema: {e}",
                operation="initialize_schema",
            )

    async def _validate_data_integrity(self) -> None:
        """Validate data integrity with error handling."""
        try:
            start_time = time.time()

            # Check for orphaned records
            orphaned_playback_records = self.connection.execute(
                """
                SELECT COUNT(*) FROM playback_history ph
                LEFT JOIN user_stats us ON ph.user_id = us.user_id
                WHERE ph.user_id IS NOT NULL AND us.user_id IS NULL
            """
            ).fetchone()[0]

            # Check for invalid surah records
            invalid_surah_records = self.connection.execute(
                """
                SELECT COUNT(*) FROM playback_history
                WHERE surah_number < 1 OR surah_number > 114
            """
            ).fetchone()[0]

            # Check for invalid bot state records
            invalid_bot_state_records = self.connection.execute(
                """
                SELECT COUNT(*) FROM bot_state
                WHERE guild_id IS NULL OR guild_id <= 0
            """
            ).fetchone()[0]

            # Log integrity check results
            TreeLogger.info(
                "Data integrity validation complete",
                {
                    "orphaned_playback_records": orphaned_playback_records,
                    "invalid_surah_records": invalid_surah_records,
                    "invalid_bot_state_records": invalid_bot_state_records,
                    "integrity_check_time_ms": (time.time() - start_time) * 1000,
                },
            )

            # Update integrity statistics
            self.integrity_stats["total_checks"] += 1
            self.integrity_stats["last_integrity_check"] = datetime.now(
                APP_TIMEZONE
            ).isoformat()

            if (
                orphaned_playback_records == 0
                and invalid_surah_records == 0
                and invalid_bot_state_records == 0
            ):
                self.integrity_stats["passed_checks"] += 1
            else:
                self.integrity_stats["failed_checks"] += 1
                self.integrity_stats["data_corruption_events"] += 1

                TreeLogger.warning(
                    "Data integrity issues detected",
                    {
                        "orphaned_playback_records": orphaned_playback_records,
                        "invalid_surah_records": invalid_surah_records,
                        "invalid_bot_state_records": invalid_bot_state_records,
                    },
                    service="DatabaseService",
                )

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "validate_data_integrity",
                    "database_path": str(self.db_path),
                },
            )
            raise DatabaseError(
                f"Failed to validate data integrity: {e}",
                operation="validate_data_integrity",
            )

    async def _setup_backup_system(self) -> None:
        """Setup automatic backup system with error handling."""
        try:
            # Ensure backup directory exists
            self.backup_dir.mkdir(parents=True, exist_ok=True)

            # Check if initial backup is needed
            if self.db_path.exists() and self.db_path.stat().st_size > 0:
                # Perform initial backup
                await self._perform_backup("initial_backup")

                # Clean up old backups if enabled
                if self.config.backup_cleanup_on_startup:
                    await self._cleanup_old_backups()
            else:
                TreeLogger.info(
                    "Initial backup skipped (no data)", service="DatabaseService"
                )

            TreeLogger.info(
                "Backup system ready",
                {
                    "backup_directory": str(self.backup_dir),
                    "backup_interval_hours": 6,  # Default backup interval
                    "initial_backup": (
                        "completed"
                        if self.backup_stats["total_backups"] > 0
                        else "skipped"
                    ),
                },
            )

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "setup_backup_system",
                    "backup_folder": str(self.backup_dir),
                },
            )
            raise DatabaseError(
                f"Failed to setup backup system: {e}", operation="setup_backup_system"
            )

    # =========================================================================
    # Background Task Management
    # =========================================================================

    async def _start_background_tasks(self) -> None:
        """Start background tasks with error handling."""
        try:
            # Start backup monitoring task
            self.backup_task = asyncio.create_task(self._backup_monitoring_loop())

            # Start integrity monitoring task
            self.integrity_task = asyncio.create_task(self._integrity_monitoring_loop())

            # Start cleanup task
            self.cleanup_task = asyncio.create_task(self._cleanup_monitoring_loop())

            TreeLogger.info(
                "Background tasks started successfully",
                {
                    "backup_monitoring": "active",
                    "integrity_monitoring": "active",
                    "cleanup_tasks": "scheduled",
                },
                service="DatabaseService",
            )

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "start_background_tasks",
                    "service_name": "DatabaseService",
                },
            )
            raise DatabaseError(
                f"Failed to start background tasks: {e}",
                operation="start_background_tasks",
            )

    async def _stop_background_tasks(self) -> None:
        """Stop background tasks with error handling."""
        try:
            # Cancel all background tasks
            tasks_to_cancel = [self.backup_task, self.integrity_task, self.cleanup_task]

            for task in tasks_to_cancel:
                if task and not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

            TreeLogger.info(
                "Background tasks stopped successfully", service="DatabaseService"
            )

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "stop_background_tasks",
                    "service_name": "DatabaseService",
                },
            )
            raise DatabaseError(
                f"Failed to stop background tasks: {e}",
                operation="stop_background_tasks",
            )

    async def _backup_monitoring_loop(self) -> None:
        """Background loop for automatic backups."""
        while True:
            try:
                await asyncio.sleep(6 * 3600)  # 6 hour backup interval
                await self._perform_backup("scheduled_backup")

            except asyncio.CancelledError:
                break
            except Exception as e:
                await self.error_handler.handle_error(
                    e,
                    {
                        "operation": "backup_monitoring_loop",
                        "service_name": "DatabaseService",
                    },
                )

    async def _integrity_monitoring_loop(self) -> None:
        """Background loop for data integrity monitoring."""
        while True:
            try:
                await asyncio.sleep(3600)  # Check every hour
                await self._validate_data_integrity()

            except asyncio.CancelledError:
                break
            except Exception as e:
                await self.error_handler.handle_error(
                    e,
                    {
                        "operation": "integrity_monitoring_loop",
                        "service_name": "DatabaseService",
                    },
                )

    async def _cleanup_monitoring_loop(self) -> None:
        """Background loop for database cleanup."""
        while True:
            try:
                await asyncio.sleep(86400)  # Cleanup every day
                await self.cleanup_old_logs(30)  # Keep logs for 30 days

            except asyncio.CancelledError:
                break
            except Exception as e:
                await self.error_handler.handle_error(
                    e,
                    {
                        "operation": "cleanup_monitoring_loop",
                        "service_name": "DatabaseService",
                    },
                )

    # =========================================================================
    # Backup Management
    # =========================================================================

    async def _perform_backup(self, backup_type: str = "scheduled") -> None:
        """
        Perform database backup with comprehensive error handling and integrity verification.

        This method performs complex database backup including:
        - Backup file creation with timestamped naming
        - File system operations and size calculation
        - Checksum calculation for integrity verification
        - Statistics tracking and monitoring
        - Error handling and recovery mechanisms
        - Performance timing and metrics

        Args:
            backup_type: Type of backup ("scheduled", "manual", "emergency")
        """
        try:
            # STEP 1: Performance Timing Initialization
            # Start timing for backup performance measurement
            # This helps track backup performance over time
            start_time = time.time()

            # STEP 2: Backup File Creation with Timestamped Naming
            # Create backup filename with timestamp for unique identification
            # This prevents backup file conflicts and enables chronological tracking
            timestamp = datetime.now(APP_TIMEZONE).strftime("%Y%m%d_%H%M%S")
            backup_filename = f"quranbot_backup_{backup_type}_{timestamp}.db"
            backup_path = self.backup_dir / backup_filename

            # STEP 3: Database File Copy Operation
            # Copy database file to backup location with metadata preservation
            # This creates a complete backup of the current database state
            shutil.copy2(self.db_path, backup_path)

            # STEP 4: Backup Size Calculation and Validation
            # Calculate backup file size for monitoring and storage management
            # This helps track backup storage requirements
            backup_size_mb = backup_path.stat().st_size / (1024 * 1024)

            # STEP 5: Checksum Calculation for Integrity Verification
            # Calculate MD5 checksum to verify backup file integrity
            # This enables detection of backup corruption during restoration
            with open(backup_path, "rb") as f:
                backup_checksum = hashlib.md5(f.read()).hexdigest()

            # STEP 6: Statistics Update and Monitoring
            # Update backup statistics for health monitoring and analytics
            # This helps track backup success rates and performance
            self.backup_stats["total_backups"] += 1
            self.backup_stats["successful_backups"] += 1
            self.backup_stats["last_backup_time"] = datetime.now(
                APP_TIMEZONE
            ).isoformat()
            self.backup_stats["backup_size_mb"] = backup_size_mb

            # STEP 7: Performance Timing and Success Logging
            # Calculate backup time and log comprehensive success information
            # This provides debugging information and performance tracking
            backup_time = time.time() - start_time

            TreeLogger.info(
                "Database backup completed successfully",
                {
                    "backup_type": backup_type,
                    "backup_path": str(backup_path),
                    "backup_size_mb": round(backup_size_mb, 2),
                    "backup_time_ms": backup_time * 1000,
                    "checksum": backup_checksum[:8] + "...",
                },
            )

            # Clean up old backups after successful backup
            # This ensures we always have the latest backup before cleaning
            await self._cleanup_old_backups()

        except Exception as e:
            # ERROR HANDLING: Comprehensive error tracking and recovery
            # This section handles all backup failures and provides debugging context
            # Update backup statistics for failure tracking
            self.backup_stats["total_backups"] += 1
            self.backup_stats["failed_backups"] += 1

            await self.error_handler.handle_error(
                e,
                {
                    "operation": "perform_backup",
                    "backup_type": backup_type,
                    "backup_folder": str(self.backup_dir),
                },
            )
            raise DatabaseError(
                f"Failed to perform backup: {e}", operation="perform_backup"
            )

    async def _cleanup_old_backups(self) -> None:
        """
        Clean up old backup files based on retention policy.

        This method implements a dual retention policy:
        1. Time-based: Remove backups older than retention days
        2. Count-based: Keep only the most recent N backups

        The stricter policy applies to ensure backup storage doesn't grow unbounded.
        """
        try:
            TreeLogger.debug(
                "Starting backup cleanup process",
                {
                    "retention_days": self.config.backup_retention_days,
                    "max_count": self.config.backup_max_count,
                    "backup_dir": str(self.backup_dir),
                },
                service="DatabaseService",
            )

            # STEP 1: Get all backup files
            backup_files = list(self.backup_dir.glob("quranbot_backup_*.db"))

            if not backup_files:
                TreeLogger.debug(
                    "No backup files found to clean up", service="DatabaseService"
                )
                return

            # STEP 2: Sort by modification time (newest first)
            backup_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

            # STEP 3: Calculate retention cutoff time
            cutoff_time = datetime.now(APP_TIMEZONE) - timedelta(
                days=self.config.backup_retention_days
            )
            cutoff_timestamp = cutoff_time.timestamp()

            files_removed = 0
            space_freed_mb = 0

            # STEP 4: Apply retention policies
            for i, backup_file in enumerate(backup_files):
                should_remove = False
                reason = ""

                # Check count-based retention
                if i >= self.config.backup_max_count:
                    should_remove = True
                    reason = f"exceeds max count ({self.config.backup_max_count})"

                # Check time-based retention
                elif backup_file.stat().st_mtime < cutoff_timestamp:
                    should_remove = True
                    file_age_days = (
                        datetime.now(APP_TIMEZONE).timestamp()
                        - backup_file.stat().st_mtime
                    ) / 86400
                    reason = f"older than {self.config.backup_retention_days} days (age: {file_age_days:.1f} days)"

                # Remove file if needed
                if should_remove:
                    file_size_mb = backup_file.stat().st_size / (1024 * 1024)

                    TreeLogger.debug(
                        f"Removing old backup: {backup_file.name}",
                        {
                            "reason": reason,
                            "size_mb": round(file_size_mb, 2),
                            "age_days": round(
                                (
                                    datetime.now(APP_TIMEZONE).timestamp()
                                    - backup_file.stat().st_mtime
                                )
                                / 86400,
                                1,
                            ),
                        },
                        service="DatabaseService",
                    )

                    backup_file.unlink()
                    files_removed += 1
                    space_freed_mb += file_size_mb

            # STEP 5: Log cleanup results
            if files_removed > 0:
                TreeLogger.info(
                    "Backup cleanup completed",
                    {
                        "files_removed": files_removed,
                        "space_freed_mb": round(space_freed_mb, 2),
                        "files_remaining": len(backup_files) - files_removed,
                        "retention_days": self.config.backup_retention_days,
                        "max_count": self.config.backup_max_count,
                    },
                    service="DatabaseService",
                )
            else:
                TreeLogger.debug(
                    "No backups needed cleanup",
                    {
                        "total_backups": len(backup_files),
                        "newest_age_days": (
                            round(
                                (
                                    datetime.now(APP_TIMEZONE).timestamp()
                                    - backup_files[0].stat().st_mtime
                                )
                                / 86400,
                                1,
                            )
                            if backup_files
                            else 0
                        ),
                    },
                    service="DatabaseService",
                )

        except Exception as e:
            # Non-critical error - log but don't fail
            TreeLogger.error(
                f"Error during backup cleanup: {e}",
                {"error_type": type(e).__name__, "backup_dir": str(self.backup_dir)},
                service="DatabaseService",
            )

            await self.error_handler.handle_error(
                e,
                {
                    "operation": "cleanup_old_backups",
                    "service_name": "DatabaseService",
                    "non_critical": True,
                },
            )

    # =========================================================================
    # Utility Methods
    # =========================================================================

    async def _verify_connection(self) -> None:
        """Verify database connection is still valid."""
        try:
            if not self.connection:
                raise DatabaseError(
                    "Database connection not established", operation="verify_connection"
                )

            # Test connection with simple query
            self.connection.execute("SELECT 1")

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {"operation": "verify_connection", "database_path": str(self.db_path)},
            )
            raise DatabaseError(
                f"Database connection verification failed: {e}",
                operation="verify_connection",
            )

    async def _log_startup_statistics(self) -> None:
        """Log startup statistics with metrics."""
        try:
            table_counts = await self._get_table_counts()

            TreeLogger.info(
                "Database startup statistics",
                {
                    "database_size_mb": round(self._get_database_size_mb(), 2),
                    "table_counts": table_counts,
                    "wal_mode_enabled": self._is_wal_mode_enabled(),
                    "available_disk_space_mb": round(
                        self._get_available_disk_space_mb(), 2
                    ),
                },
            )

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "log_startup_statistics",
                    "service_name": "DatabaseService",
                },
            )

    async def _log_final_statistics(self) -> None:
        """Log final statistics with metrics."""
        try:
            TreeLogger.info(
                "Database final statistics",
                {
                    "total_queries": self.query_stats.total_queries,
                    "success_rate": f"{self._get_success_rate():.1f}%",
                    "total_backups": self.backup_stats["total_backups"],
                    "backup_success_rate": f"{(self.backup_stats['successful_backups'] / max(self.backup_stats['total_backups'], 1)) * 100:.1f}%",
                    "integrity_checks": self.integrity_stats["total_checks"],
                    "corruption_events": self.integrity_stats["data_corruption_events"],
                },
            )

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "log_final_statistics",
                    "service_name": "DatabaseService",
                },
            )

    async def _get_table_counts(self) -> dict[str, int]:
        """Get record counts for all tables."""
        try:
            counts = {}

            for table in ["user_stats", "bot_state", "playback_history", "system_logs"]:
                result = self.connection.execute(
                    f"SELECT COUNT(*) FROM {table}"
                ).fetchone()
                counts[table] = result[0] if result else 0

            return counts

        except Exception as e:
            await self.error_handler.handle_error(
                e, {"operation": "get_table_counts", "service_name": "DatabaseService"}
            )
            return {}

    def _get_database_size_mb(self) -> float:
        """Get database file size in MB."""
        try:
            if self.db_path.exists():
                return self.db_path.stat().st_size / (1024 * 1024)
            return 0.0
        except Exception:
            return 0.0

    def _get_available_disk_space_mb(self) -> float:
        """Get available disk space in MB."""
        try:
            import shutil

            total, used, free = shutil.disk_usage(self.db_path.parent)
            return free / (1024 * 1024)
        except Exception:
            return 0.0

    def _get_success_rate(self) -> float:
        """Get query success rate percentage."""
        if self.query_stats.total_queries == 0:
            return 100.0
        return (
            self.query_stats.successful_queries / self.query_stats.total_queries
        ) * 100

    def _is_wal_mode_enabled(self) -> bool:
        """Check if WAL mode is enabled."""
        try:
            result = self.connection.execute("PRAGMA journal_mode").fetchone()
            return result and result[0] == "wal"
        except Exception:
            return False

    def _update_query_stats(
        self, query_time: float, success: bool, query_type: str = "unknown"
    ) -> None:
        """Update query statistics."""
        self.query_stats.update(query_time, success, query_type)

    # =========================================================================
    # Public Interface with Retry Logic
    # =========================================================================

    async def get_user_stats(self, user_id: int) -> dict[str, Any] | None:
        """Get user statistics with error handling and retry logic."""
        try:
            start_time = time.time()

            result = await self._retry_operation(
                operation=lambda: self._execute_query(
                    "SELECT * FROM user_stats WHERE user_id = ?", (user_id,), "SELECT"
                ),
                operation_name="get_user_stats",
                context={"user_id": user_id, "query_type": "SELECT"},
            )

            query_time = time.time() - start_time
            self._update_query_stats(query_time, True, "SELECT")

            if result:
                return dict(result)
            return None

        except Exception as e:
            query_time = time.time() - start_time if "start_time" in locals() else 0
            self._update_query_stats(query_time, False, "SELECT")

            await self.error_handler.handle_error(
                e,
                {
                    "operation": "get_user_stats",
                    "user_id": user_id,
                    "query_type": "SELECT",
                },
            )
            return None

    async def create_user_stats(self, user_id: int, username: str) -> dict[str, Any]:
        """Create user statistics with error handling and retry logic."""
        try:
            start_time = time.time()

            result = await self._retry_operation(
                operation=lambda: self._execute_query(
                    """
                    INSERT INTO user_stats (user_id, username, total_playbacks, total_duration_seconds)
                    VALUES (?, ?, 0, 0.0)
                    """,
                    (user_id, username),
                    "INSERT",
                ),
                operation_name="create_user_stats",
                context={
                    "user_id": user_id,
                    "username": username,
                    "query_type": "INSERT",
                },
            )

            query_time = time.time() - start_time
            self._update_query_stats(query_time, True, "INSERT")

            return {
                "user_id": user_id,
                "username": username,
                "total_playbacks": 0,
                "total_duration_seconds": 0.0,
                "favorite_reciter": None,
                "last_activity": datetime.now(APP_TIMEZONE).isoformat(),
                "created_at": datetime.now(APP_TIMEZONE).isoformat(),
                "updated_at": datetime.now(APP_TIMEZONE).isoformat(),
            }

        except Exception as e:
            query_time = time.time() - start_time if "start_time" in locals() else 0
            self._update_query_stats(query_time, False, "INSERT")

            await self.error_handler.handle_error(
                e,
                {
                    "operation": "create_user_stats",
                    "user_id": user_id,
                    "username": username,
                    "query_type": "INSERT",
                },
            )
            raise DatabaseError(
                f"Failed to create user stats: {e}", operation="create_user_stats"
            )

    async def _execute_query(
        self, query: str, params: tuple, query_type: str
    ) -> sqlite3.Row | None:
        """Execute database query with error handling."""
        try:
            TreeLogger.debug(
                f"Executing {query_type} query",
                {
                    "query": query[:100] + "..." if len(query) > 100 else query,
                    "params_count": len(params),
                    "has_params": bool(params),
                },
                service="DatabaseService",
            )

            start_time = time.time()
            cursor = self.connection.execute(query, params)

            if query_type.upper() in ["SELECT"]:
                result = cursor.fetchone()
                TreeLogger.debug(
                    f"Query completed in {(time.time() - start_time)*1000:.2f}ms",
                    {"query_type": query_type, "has_result": bool(result)},
                    service="DatabaseService",
                )
                return result
            else:
                self.connection.commit()
                TreeLogger.debug(
                    f"Query committed in {(time.time() - start_time)*1000:.2f}ms",
                    {"query_type": query_type, "rows_affected": cursor.rowcount},
                    service="DatabaseService",
                )
                return None

        except Exception as e:
            self.connection.rollback()
            raise DatabaseError(
                f"Query execution failed: {e}",
                operation="execute_query",
                additional_context={
                    "query": query,
                    "params": params,
                    "query_type": query_type,
                },
            )

    async def cleanup_old_logs(self, days: int = 30) -> int:
        """Clean up old system logs with error handling."""
        try:
            start_time = time.time()

            result = await self._retry_operation(
                operation=lambda: self._execute_query(
                    f"DELETE FROM system_logs WHERE timestamp < datetime('now', '-{days} days')",
                    (),
                    "DELETE",
                ),
                operation_name="cleanup_old_logs",
                context={"days": days, "query_type": "DELETE"},
            )

            query_time = time.time() - start_time
            self._update_query_stats(query_time, True, "DELETE")

            # Get the number of deleted rows
            deleted_count = self.connection.total_changes

            TreeLogger.info(
                f"Cleaned up {deleted_count} old log entries",
                {
                    "deleted_count": deleted_count,
                    "days_old": days,
                    "cleanup_time_ms": query_time * 1000,
                },
                service="DatabaseService",
            )

            return deleted_count

        except Exception as e:
            query_time = time.time() - start_time if "start_time" in locals() else 0
            self._update_query_stats(query_time, False, "DELETE")

            await self.error_handler.handle_error(
                e,
                {"operation": "cleanup_old_logs", "days": days, "query_type": "DELETE"},
            )
            return 0

    async def execute(self, query: str, params: tuple | None = None) -> sqlite3.Cursor:
        """
        Execute a database query.

        Args:
            query: SQL query to execute
            params: Query parameters

        Returns:
            Cursor object
        """
        start_time = time.time()

        try:
            TreeLogger.debug(
                "Executing query",
                {
                    "query_preview": query[:100] + "..." if len(query) > 100 else query,
                    "has_params": params is not None,
                },
                service=self.service_name,
            )

            if not self.connection:
                raise ConnectionError("Database connection not established")

            cursor = self.connection.cursor()

            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            # Commit if it's a write operation
            if (
                query.strip()
                .upper()
                .startswith(("INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP"))
            ):
                self.connection.commit()

            query_time = time.time() - start_time
            self._update_query_stats(query_time, True, query.strip().split()[0].upper())

            TreeLogger.debug(
                "Query executed successfully",
                {"query_time_ms": round(query_time * 1000, 2)},
                service=self.service_name,
            )

            return cursor

        except Exception as e:
            query_time = time.time() - start_time
            self._update_query_stats(
                query_time, False, query.strip().split()[0].upper()
            )

            TreeLogger.error(
                "Database query failed",
                e,
                {
                    "query_preview": query[:100] + "..." if len(query) > 100 else query,
                    "error_type": type(e).__name__,
                },
                service=self.service_name,
            )

            await self.error_handler.handle_error(
                e,
                {
                    "operation": "execute_query",
                    "query": query[:100],
                    "has_params": params is not None,
                },
            )
            raise

    async def fetch_one(
        self, query: str, params: tuple | None = None
    ) -> dict[str, Any] | None:
        """
        Execute a query and fetch one result.

        Args:
            query: SQL query to execute
            params: Query parameters

        Returns:
            Dictionary with column names as keys, or None if no result
        """
        try:
            cursor = await self.execute(query, params)
            row = cursor.fetchone()

            if row:
                # Convert to dictionary
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row, strict=False))

            return None

        except Exception as e:
            TreeLogger.error(
                "Failed to fetch one",
                e,
                {"query_preview": query[:100] + "..." if len(query) > 100 else query},
                service=self.service_name,
            )

            await self.error_handler.handle_error(
                e, {"operation": "fetch_one", "query": query[:100]}
            )
            return None

    async def fetch_all(
        self, query: str, params: tuple | None = None
    ) -> list[dict[str, Any]]:
        """
        Execute a query and fetch all results.

        Args:
            query: SQL query to execute
            params: Query parameters

        Returns:
            List of dictionaries with column names as keys
        """
        try:
            cursor = await self.execute(query, params)
            rows = cursor.fetchall()

            if rows:
                # Convert to list of dictionaries
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row, strict=False)) for row in rows]

            return []

        except Exception as e:
            TreeLogger.error(
                "Failed to fetch all",
                e,
                {"query_preview": query[:100] + "..." if len(query) > 100 else query},
                service=self.service_name,
            )

            await self.error_handler.handle_error(
                e, {"operation": "fetch_all", "query": query[:100]}
            )
            return []
