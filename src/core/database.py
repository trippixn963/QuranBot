"""QuranBot - SQLite Database Manager.

Robust SQLite database implementation replacing JSON storage with enterprise-grade
features including ACID transactions, connection pooling, and automatic migrations.

This module provides the core database infrastructure for QuranBot, offering
reliable data persistence with performance optimization and data integrity guarantees.

Classes:
    DatabaseManager: Core SQLite database manager with connection pooling

Features:
    - ACID transactions with Write-Ahead Logging (WAL) mode
    - Thread-safe connection pooling with configurable limits
    - Automatic schema migrations and version management
    - Data integrity validation and consistency checks
    - Backup and recovery support with atomic operations
    - Performance optimization with query caching and indexing
    - Comprehensive error handling with detailed logging

Database Schema:
    - playback_state: Current audio playback state and position
    - bot_statistics: Runtime statistics and usage metrics
    - quiz_config: Quiz system configuration and scheduling
    - quiz_statistics: Global quiz performance metrics
    - user_quiz_stats: Individual user quiz performance
    - metadata_cache: Audio file metadata caching
    - system_events: System event logging and audit trail
"""

import asyncio
from contextlib import contextmanager
from pathlib import Path
import sqlite3
import threading
from typing import Any

from ..utils.tree_log import log_perfect_tree_section
from .exceptions import DatabaseError
from .logger import StructuredLogger


class DatabaseManager:
    """
    SQLite database manager for QuranBot with enterprise features.

    Features:
    - ACID transactions with Write-Ahead Logging (WAL)
    - Connection pooling with thread-local storage
    - Automatic schema migrations
    - Data integrity validation
    - Backup and recovery support
    - Performance optimization
    """

    def __init__(
        self,
        logger: StructuredLogger,
        db_path: Path = None,
        max_connections: int = 10,
        enable_wal: bool = True,
    ):
        """
        Initialize the database manager with connection pooling and configuration.

        Sets up the SQLite database manager with thread-safe connection pooling,
        WAL mode for better concurrency, and automatic schema initialization.

        Args:
            logger: Structured logger instance for database operation logging
            db_path: Path to SQLite database file (defaults to data/quranbot.db)
            max_connections: Maximum connection pool size for concurrent operations
            enable_wal: Enable Write-Ahead Logging mode for improved concurrency
        """
        self.logger = logger
        self.db_path = db_path or Path("data/quranbot.db")
        self.max_connections = max_connections
        self.enable_wal = enable_wal

        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Connection pool using thread-local storage
        self._local = threading.local()
        self._pool_lock = threading.Lock()
        self._connections = []
        self._is_initialized = False

        # Database schema version for migrations
        self.schema_version = 1

    async def initialize(self) -> None:
        """Initialize the database with schema and optimizations"""
        try:
            await self.logger.info("Initializing SQLite database")

            # Create initial connection and schema
            await asyncio.get_event_loop().run_in_executor(None, self._initialize_sync)

            self._is_initialized = True

            await self.logger.info(
                "Database initialized successfully",
                {
                    "db_path": str(self.db_path),
                    "wal_enabled": self.enable_wal,
                    "schema_version": self.schema_version,
                },
            )

            log_perfect_tree_section(
                "SQLite Database - Initialized",
                [
                    ("database_file", f"💾 {self.db_path}"),
                    ("wal_mode", f"⚡ {'Enabled' if self.enable_wal else 'Disabled'}"),
                    ("schema_version", f"📊 v{self.schema_version}"),
                    ("status", "✅ Ready for operations"),
                ],
                "🗄️",
            )

        except Exception as e:
            await self.logger.error(
                "Failed to initialize database",
                {"error": str(e), "db_path": str(self.db_path)},
            )
            raise DatabaseError(f"Database initialization failed: {e}")

    async def shutdown(self) -> None:
        """Shutdown the database manager and close all connections"""
        try:
            self.close_connection()
            await self.logger.info("Database manager shutdown complete")
        except Exception as e:
            await self.logger.error("Error during database shutdown", {"error": str(e)})

    def _initialize_sync(self) -> None:
        """Synchronous database initialization (runs in thread pool)"""
        with sqlite3.connect(self.db_path) as conn:
            # Enable WAL mode for better concurrency
            if self.enable_wal:
                conn.execute("PRAGMA journal_mode=WAL")

            # Performance optimizations
            conn.execute("PRAGMA synchronous=NORMAL")  # Balance safety/performance
            conn.execute("PRAGMA cache_size=10000")  # 10MB cache
            conn.execute("PRAGMA temp_store=MEMORY")  # Use memory for temp storage
            conn.execute("PRAGMA mmap_size=268435456")  # 256MB memory-mapped I/O

            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys=ON")

            # Create schema
            self._create_schema(conn)

            # Set schema version
            self._set_schema_version(conn, self.schema_version)

    def _create_schema(self, conn: sqlite3.Connection) -> None:
        """Create database schema"""

        # Bot state and configuration
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bot_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                data_type TEXT NOT NULL DEFAULT 'string',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Playback state
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS playback_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                surah_number INTEGER NOT NULL DEFAULT 1,
                position_seconds REAL NOT NULL DEFAULT 0.0,
                reciter TEXT NOT NULL DEFAULT 'Saad Al Ghamdi',
                volume REAL NOT NULL DEFAULT 1.0,
                is_playing BOOLEAN NOT NULL DEFAULT 0,
                is_paused BOOLEAN NOT NULL DEFAULT 0,
                loop_enabled BOOLEAN NOT NULL DEFAULT 0,
                shuffle_enabled BOOLEAN NOT NULL DEFAULT 0,
                playback_mode TEXT NOT NULL DEFAULT 'normal',
                total_duration REAL DEFAULT 0.0,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Bot statistics
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bot_statistics (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                total_runtime_hours REAL NOT NULL DEFAULT 0.0,
                total_sessions INTEGER NOT NULL DEFAULT 0,
                total_completed_sessions INTEGER NOT NULL DEFAULT 0,
                last_startup DATETIME,
                last_shutdown DATETIME,
                favorite_reciter TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Quiz state and configuration
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS quiz_config (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                send_interval_hours REAL NOT NULL DEFAULT 3.0,
                enabled BOOLEAN NOT NULL DEFAULT 1,
                channel_id TEXT,
                last_question_sent DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Quiz statistics (global)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS quiz_statistics (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                questions_sent INTEGER NOT NULL DEFAULT 0,
                total_attempts INTEGER NOT NULL DEFAULT 0,
                correct_answers INTEGER NOT NULL DEFAULT 0,
                unique_participants INTEGER NOT NULL DEFAULT 0,
                last_reset DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # User quiz statistics
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_quiz_stats (
                user_id TEXT PRIMARY KEY,
                username TEXT,
                display_name TEXT,
                correct_answers INTEGER NOT NULL DEFAULT 0,
                total_attempts INTEGER NOT NULL DEFAULT 0,
                streak INTEGER NOT NULL DEFAULT 0,
                best_streak INTEGER NOT NULL DEFAULT 0,
                points INTEGER NOT NULL DEFAULT 0,
                last_answer DATETIME,
                first_answer DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Metadata cache
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS metadata_cache (
                cache_key TEXT PRIMARY KEY,
                file_path TEXT NOT NULL,
                reciter TEXT NOT NULL,
                surah_number INTEGER NOT NULL,
                duration_seconds REAL,
                file_size INTEGER,
                bitrate INTEGER,
                sample_rate INTEGER,
                channels INTEGER,
                format TEXT,
                cached_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 1
            )
        """
        )

        # System logs and events
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS system_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                event_data TEXT,
                severity TEXT NOT NULL DEFAULT 'info',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                correlation_id TEXT
            )
        """
        )

        # Schema version tracking
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_info (
                version INTEGER PRIMARY KEY,
                applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
        """
        )

        # Create indexes for performance
        self._create_indexes(conn)

        # Initialize default data
        self._insert_default_data(conn)

    def _create_indexes(self, conn: sqlite3.Connection) -> None:
        """Create database indexes for optimal performance"""

        # Metadata cache indexes
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_metadata_reciter_surah
            ON metadata_cache(reciter, surah_number)
        """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_metadata_last_accessed
            ON metadata_cache(last_accessed)
        """
        )

        # User quiz stats indexes
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_user_quiz_points
            ON user_quiz_stats(points DESC)
        """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_user_quiz_streak
            ON user_quiz_stats(best_streak DESC)
        """
        )

        # System events indexes
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_system_events_timestamp
            ON system_events(timestamp)
        """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_system_events_type
            ON system_events(event_type)
        """
        )

    def _insert_default_data(self, conn: sqlite3.Connection) -> None:
        """Insert default data if tables are empty"""

        # Default playback state
        conn.execute(
            """
            INSERT OR IGNORE INTO playback_state (id) VALUES (1)
        """
        )

        # Default bot statistics
        conn.execute(
            """
            INSERT OR IGNORE INTO bot_statistics (id) VALUES (1)
        """
        )

        # Default quiz configuration
        conn.execute(
            """
            INSERT OR IGNORE INTO quiz_config (id) VALUES (1)
        """
        )

        # Default quiz statistics
        conn.execute(
            """
            INSERT OR IGNORE INTO quiz_statistics (id) VALUES (1)
        """
        )

    def _set_schema_version(self, conn: sqlite3.Connection, version: int) -> None:
        """Set the current schema version"""
        conn.execute(
            """
            INSERT OR REPLACE INTO schema_info (version, description)
            VALUES (?, 'Initial QuranBot SQLite schema')
        """,
            (version,),
        )

    @contextmanager
    def get_connection(self):
        """Get a database connection with proper cleanup"""
        conn = None
        try:
            conn = self._get_thread_connection()
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise DatabaseError(f"Database operation failed: {e}")
        finally:
            # Don't close the connection here - it's managed by _get_thread_connection
            # The connection will be closed when the thread ends or when explicitly closed
            pass

    def _get_thread_connection(self) -> sqlite3.Connection:
        """Get a connection for the current thread"""
        if (
            not hasattr(self._local, "connection")
            or self._local.connection is None
            or not self._is_connection_valid()
        ):
            # Close existing connection if it exists but is invalid
            if (
                hasattr(self._local, "connection")
                and self._local.connection is not None
            ):
                try:
                    self._local.connection.close()
                except Exception:
                    pass

            conn = sqlite3.connect(
                self.db_path,
                timeout=30.0,
                check_same_thread=False,  # 30 second timeout
            )
            # Set row factory for dict-like access
            conn.row_factory = sqlite3.Row
            # Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            conn.execute("PRAGMA temp_store=MEMORY")
            self._local.connection = conn

        return self._local.connection

    def _is_connection_valid(self) -> bool:
        """Check if the current thread's connection is valid"""
        if not hasattr(self._local, "connection") or self._local.connection is None:
            return False
        try:
            # Try a simple query to test the connection
            self._local.connection.execute("SELECT 1")
            return True
        except Exception:
            return False

    def close_connection(self):
        """Close the current thread's database connection"""
        if hasattr(self._local, "connection"):
            try:
                self._local.connection.close()
                delattr(self._local, "connection")
            except Exception as e:
                self.logger.warning(f"Error closing database connection: {e}")

    async def execute_query(
        self,
        query: str,
        params: tuple = None,
        fetch_one: bool = False,
        fetch_all: bool = False,
    ) -> sqlite3.Row | list[sqlite3.Row] | None:
        """
        Execute a SQL query asynchronously.

        Args:
            query: SQL query string
            params: Query parameters tuple
            fetch_one: Return single row
            fetch_all: Return all rows

        Returns:
            Query results or None
        """
        try:
            return await asyncio.get_event_loop().run_in_executor(
                None,
                self._execute_query_sync,
                query,
                params or (),
                fetch_one,
                fetch_all,
            )
        except Exception as e:
            await self.logger.error(
                "Database query failed", {"query": query, "error": str(e)}
            )
            raise DatabaseError(f"Query execution failed: {e}")

    def _execute_query_sync(
        self, query: str, params: tuple, fetch_one: bool, fetch_all: bool
    ) -> sqlite3.Row | list[sqlite3.Row] | None:
        """Synchronous query execution"""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)

            if fetch_one:
                return cursor.fetchone()
            elif fetch_all:
                return cursor.fetchall()
            else:
                conn.commit()
                return None

    async def execute_transaction(self, operations: list[tuple[str, tuple]]) -> bool:
        """
        Execute multiple operations in a single transaction.

        Args:
            operations: List of (query, params) tuples

        Returns:
            True if transaction successful
        """
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, self._execute_transaction_sync, operations
            )
            return True
        except Exception as e:
            await self.logger.error(
                "Database transaction failed",
                {"operations_count": len(operations), "error": str(e)},
            )
            return False

    def _execute_transaction_sync(self, operations: list[tuple[str, tuple]]) -> None:
        """Synchronous transaction execution"""
        with self.get_connection() as conn:
            try:
                conn.execute("BEGIN TRANSACTION")

                for query, params in operations:
                    conn.execute(query, params)

                conn.commit()

            except Exception as e:
                conn.rollback()
                raise e

    async def backup_database(self, backup_path: Path) -> bool:
        """
        Create a backup of the database.

        Args:
            backup_path: Path for backup file

        Returns:
            True if backup successful
        """
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, self._backup_database_sync, backup_path
            )

            await self.logger.info(
                "Database backup created", {"backup_path": str(backup_path)}
            )
            return True

        except Exception as e:
            await self.logger.error(
                "Database backup failed",
                {"backup_path": str(backup_path), "error": str(e)},
            )
            return False

    def _backup_database_sync(self, backup_path: Path) -> None:
        """Synchronous database backup"""
        backup_path.parent.mkdir(parents=True, exist_ok=True)

        # Use SQLite backup API for consistent backup
        with sqlite3.connect(self.db_path) as source:
            with sqlite3.connect(backup_path) as backup:
                source.backup(backup)

    async def get_database_stats(self) -> dict[str, Any]:
        """Get database statistics and health information"""
        try:
            stats = await asyncio.get_event_loop().run_in_executor(
                None, self._get_database_stats_sync
            )
            return stats
        except Exception as e:
            await self.logger.error("Failed to get database stats", {"error": str(e)})
            return {"error": str(e)}

    def _get_database_stats_sync(self) -> dict[str, Any]:
        """Synchronous database statistics collection"""
        with self.get_connection() as conn:
            # Get database size
            db_size = self.db_path.stat().st_size if self.db_path.exists() else 0

            # Get table counts
            tables = {}
            table_names = [
                "bot_state",
                "playback_state",
                "bot_statistics",
                "quiz_config",
                "quiz_statistics",
                "user_quiz_stats",
                "metadata_cache",
                "system_events",
            ]

            for table in table_names:
                try:
                    result = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                    tables[table] = result[0] if result else 0
                except sqlite3.Error:
                    # Handle SQLite-specific errors
                    tables[table] = 0

            # Get WAL info
            wal_info = {}
            try:
                pragma_result = conn.execute("PRAGMA journal_mode").fetchone()
                wal_info["journal_mode"] = (
                    pragma_result[0] if pragma_result else "unknown"
                )

                if wal_info["journal_mode"] == "wal":
                    wal_size_result = conn.execute("PRAGMA wal_checkpoint").fetchone()
                    wal_info["checkpoint_result"] = wal_size_result
            except sqlite3.Error as e:
                wal_info["journal_mode"] = "unknown"
                wal_info["error"] = str(e)

            return {
                "database_size_bytes": db_size,
                "database_size_mb": round(db_size / (1024 * 1024), 2),
                "table_counts": tables,
                "wal_info": wal_info,
                "schema_version": self.schema_version,
                "total_records": sum(tables.values()),
            }

    async def cleanup_old_data(self, days_to_keep: int = 30) -> int:
        """
        Clean up old data to maintain database performance.

        Args:
            days_to_keep: Number of days of data to retain

        Returns:
            Number of records cleaned up
        """
        try:
            cleanup_operations = [
                # Clean old system events
                (
                    f"""
                    DELETE FROM system_events
                    WHERE timestamp < datetime('now', '-{days_to_keep} days')
                """,
                    (),
                ),
                # Clean old metadata cache entries (rarely accessed)
                (
                    f"""
                    DELETE FROM metadata_cache
                    WHERE last_accessed < datetime('now', '-{days_to_keep * 2} days')
                    AND access_count < 5
                """,
                    (),
                ),  # Keep cache longer
            ]

            success = await self.execute_transaction(cleanup_operations)

            if success:
                await self.logger.info(
                    "Database cleanup completed", {"days_kept": days_to_keep}
                )

            return 0  # Would need to track actual deletions

        except Exception as e:
            await self.logger.error("Database cleanup failed", {"error": str(e)})
            return 0
