# =============================================================================
# QuranBot - Connection Pool Service
# =============================================================================
# High-performance connection pooling for database operations with health
# checking, automatic failover, and intelligent resource management.
# =============================================================================

from abc import ABC, abstractmethod
import asyncio
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
import sqlite3
import time
from typing import Any, AsyncContextManager, TypeVar
import weakref

import aiofiles
import aiohttp

from .di_container import DIContainer
from .exceptions import ConfigurationError, ServiceError, handle_errors
from .logger import StructuredLogger

T = TypeVar("T")


class ConnectionType(str, Enum):
    """Types of connections supported"""

    SQLITE = "sqlite"
    HTTP = "http"
    FILE = "file"
    WEBHOOK = "webhook"


class ConnectionStatus(str, Enum):
    """Connection status states"""

    IDLE = "idle"
    ACTIVE = "active"
    FAILED = "failed"
    MAINTENANCE = "maintenance"


@dataclass
class ConnectionConfig:
    """Configuration for a connection"""

    connection_type: ConnectionType
    connection_string: str
    max_connections: int = field(default=10)
    min_connections: int = field(default=2)
    max_idle_time: int = field(default=300)  # 5 minutes
    connection_timeout: int = field(default=30)
    retry_attempts: int = field(default=3)
    retry_delay: float = field(default=1.0)
    health_check_interval: int = field(default=60)  # 1 minute
    enable_health_checks: bool = field(default=True)
    enable_metrics: bool = field(default=True)
    extra_params: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConnectionMetrics:
    """Connection pool metrics"""

    total_connections: int = field(default=0)
    active_connections: int = field(default=0)
    idle_connections: int = field(default=0)
    failed_connections: int = field(default=0)
    total_requests: int = field(default=0)
    successful_requests: int = field(default=0)
    failed_requests: int = field(default=0)
    average_response_time_ms: float = field(default=0.0)
    connection_creation_count: int = field(default=0)
    connection_destruction_count: int = field(default=0)

    @property
    def success_rate(self) -> float:
        """Calculate request success rate"""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests

    @property
    def utilization_rate(self) -> float:
        """Calculate connection utilization rate"""
        if self.total_connections == 0:
            return 0.0
        return self.active_connections / self.total_connections


@dataclass
class PooledConnection:
    """Represents a pooled connection with metadata"""

    connection: Any
    connection_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_used: datetime = field(default_factory=lambda: datetime.now(UTC))
    usage_count: int = field(default=0)
    status: ConnectionStatus = field(default=ConnectionStatus.IDLE)
    health_check_failures: int = field(default=0)

    @property
    def age_seconds(self) -> float:
        """Get connection age in seconds"""
        return (datetime.now(UTC) - self.created_at).total_seconds()

    @property
    def idle_time_seconds(self) -> float:
        """Get idle time in seconds"""
        return (datetime.now(UTC) - self.last_used).total_seconds()

    def mark_used(self) -> None:
        """Mark connection as used"""
        self.last_used = datetime.now(UTC)
        self.usage_count += 1
        self.status = ConnectionStatus.ACTIVE

    def mark_idle(self) -> None:
        """Mark connection as idle"""
        self.status = ConnectionStatus.IDLE

    def mark_failed(self) -> None:
        """Mark connection as failed"""
        self.status = ConnectionStatus.FAILED
        self.health_check_failures += 1


class ConnectionFactory(ABC):
    """Abstract factory for creating connections"""

    @abstractmethod
    async def create_connection(self, config: ConnectionConfig) -> Any:
        """Create a new connection"""
        pass

    @abstractmethod
    async def health_check(self, connection: Any) -> bool:
        """Check if connection is healthy"""
        pass

    @abstractmethod
    async def close_connection(self, connection: Any) -> None:
        """Close a connection"""
        pass


class SQLiteConnectionFactory(ConnectionFactory):
    """Factory for SQLite connections"""

    async def create_connection(self, config: ConnectionConfig) -> sqlite3.Connection:
        """Create SQLite connection"""
        try:
            db_path = config.connection_string

            # Create directory if it doesn't exist
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

            conn = sqlite3.connect(
                db_path,
                timeout=config.connection_timeout,
                check_same_thread=False,
                **config.extra_params,
            )

            # Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            conn.execute("PRAGMA temp_store=memory")

            return conn

        except Exception as e:
            raise ServiceError(f"Failed to create SQLite connection: {e!s}")

    async def health_check(self, connection: sqlite3.Connection) -> bool:
        """Check SQLite connection health"""
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            return True
        except Exception:
            return False

    async def close_connection(self, connection: sqlite3.Connection) -> None:
        """Close SQLite connection"""
        try:
            connection.close()
        except Exception:
            pass


class HTTPConnectionFactory(ConnectionFactory):
    """Factory for HTTP connections"""

    async def create_connection(
        self, config: ConnectionConfig
    ) -> aiohttp.ClientSession:
        """Create HTTP session"""
        try:
            timeout = aiohttp.ClientTimeout(total=config.connection_timeout)

            session = aiohttp.ClientSession(
                timeout=timeout,
                connector=aiohttp.TCPConnector(
                    limit=config.max_connections, limit_per_host=config.max_connections
                ),
                **config.extra_params,
            )

            return session

        except Exception as e:
            raise ServiceError(f"Failed to create HTTP session: {e!s}")

    async def health_check(self, connection: aiohttp.ClientSession) -> bool:
        """Check HTTP session health"""
        try:
            return not connection.closed
        except Exception:
            return False

    async def close_connection(self, connection: aiohttp.ClientSession) -> None:
        """Close HTTP session"""
        try:
            await connection.close()
        except Exception:
            pass


class FileConnectionFactory(ConnectionFactory):
    """Factory for file connections (async file handles)"""

    async def create_connection(
        self, config: ConnectionConfig
    ) -> aiofiles.threadpool.text.AsyncTextIOWrapper:
        """Create async file connection"""
        try:
            file_path = config.connection_string
            mode = config.extra_params.get("mode", "r")

            # Create directory if needed
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)

            file_handle = await aiofiles.open(
                file_path,
                mode=mode,
                **{k: v for k, v in config.extra_params.items() if k != "mode"},
            )

            return file_handle

        except Exception as e:
            raise ServiceError(f"Failed to create file connection: {e!s}")

    async def health_check(
        self, connection: aiofiles.threadpool.text.AsyncTextIOWrapper
    ) -> bool:
        """Check file connection health"""
        try:
            return not connection.closed
        except Exception:
            return False

    async def close_connection(
        self, connection: aiofiles.threadpool.text.AsyncTextIOWrapper
    ) -> None:
        """Close file connection"""
        try:
            await connection.close()
        except Exception:
            pass


class ConnectionPool:
    """
    High-performance connection pool with health monitoring and failover.

    Features:
    - Multiple connection types (SQLite, HTTP, File, etc.)
    - Automatic connection health checking
    - Connection lifecycle management
    - Performance metrics and monitoring
    - Graceful degradation and error recovery
    - Resource cleanup and leak prevention
    """

    def __init__(
        self,
        container: DIContainer,
        config: ConnectionConfig,
        logger: StructuredLogger | None = None,
    ):
        """Initialize connection pool"""
        self._container = container
        self._config = config
        self._logger = logger or StructuredLogger()

        # Connection storage
        self._connections: dict[str, PooledConnection] = {}
        self._idle_queue = deque()
        self._active_connections: set[str] = set()

        # Connection factory
        self._factory = self._create_factory()

        # Pool management
        self._pool_lock = asyncio.Lock()
        self._connection_semaphore = asyncio.Semaphore(config.max_connections)

        # Metrics and monitoring
        self._metrics = ConnectionMetrics()
        self._response_times: list[float] = []

        # Background tasks
        self._health_check_task: asyncio.Task | None = None
        self._cleanup_task: asyncio.Task | None = None

        # Shutdown management
        self._shutdown_event = asyncio.Event()

        # Weak references for cleanup
        self._weak_refs: weakref.WeakSet = weakref.WeakSet()

    @handle_errors
    async def initialize(self) -> None:
        """Initialize the connection pool"""
        await self._logger.info(
            "Initializing connection pool",
            {
                "type": self._config.connection_type.value,
                "min_connections": self._config.min_connections,
                "max_connections": self._config.max_connections,
            },
        )

        # Create minimum connections
        for _ in range(self._config.min_connections):
            try:
                await self._create_connection()
            except Exception as e:
                await self._logger.warning(
                    "Failed to create initial connection", {"error": str(e)}
                )

        # Start background tasks
        if self._config.enable_health_checks:
            self._health_check_task = asyncio.create_task(self._health_check_loop())

        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        await self._logger.info(
            "Connection pool initialized",
            {"initial_connections": len(self._connections)},
        )

    @handle_errors
    async def shutdown(self) -> None:
        """Shutdown the connection pool"""
        await self._logger.info("Shutting down connection pool")

        # Signal shutdown
        self._shutdown_event.set()

        # Cancel background tasks
        for task in [self._health_check_task, self._cleanup_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Close all connections
        async with self._pool_lock:
            for pooled_conn in list(self._connections.values()):
                await self._close_connection(pooled_conn)

        await self._logger.info("Connection pool shutdown complete")

    @asynccontextmanager
    async def get_connection(self) -> AsyncContextManager[Any]:
        """
        Get a connection from the pool using context manager.

        Usage:
            async with pool.get_connection() as conn:
                # Use connection
                pass
        """
        connection_id = None
        start_time = time.time()

        try:
            # Acquire semaphore
            await self._connection_semaphore.acquire()

            # Get connection
            pooled_conn = await self._acquire_connection()
            connection_id = pooled_conn.connection_id

            # Mark as active
            pooled_conn.mark_used()
            self._active_connections.add(connection_id)

            # Update metrics
            self._metrics.total_requests += 1

            yield pooled_conn.connection

            # Mark request as successful
            self._metrics.successful_requests += 1

        except Exception as e:
            # Mark request as failed
            self._metrics.failed_requests += 1
            await self._logger.error(
                "Connection usage failed",
                {"connection_id": connection_id, "error": str(e)},
            )
            raise

        finally:
            # Track response time
            response_time = time.time() - start_time
            self._response_times.append(response_time)
            if len(self._response_times) > 1000:  # Keep last 1000 measurements
                self._response_times.pop(0)

            # Update average response time
            if self._response_times:
                self._metrics.average_response_time_ms = (
                    sum(self._response_times) / len(self._response_times) * 1000
                )

            # Release connection
            if connection_id:
                await self._release_connection(connection_id)

            # Release semaphore
            self._connection_semaphore.release()

    @handle_errors
    async def execute_query(
        self, query: str, params: tuple | None = None
    ) -> list[dict[str, Any]]:
        """Execute SQL query (for SQLite connections)"""
        if self._config.connection_type != ConnectionType.SQLITE:
            raise ServiceError("execute_query only supports SQLite connections")

        async with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)

                # Fetch results if it's a SELECT query
                if query.strip().upper().startswith("SELECT"):
                    columns = [description[0] for description in cursor.description]
                    rows = cursor.fetchall()
                    return [dict(zip(columns, row, strict=False)) for row in rows]
                else:
                    conn.commit()
                    return []

            finally:
                cursor.close()

    @handle_errors
    async def execute_http_request(
        self, method: str, url: str, **kwargs
    ) -> aiohttp.ClientResponse:
        """Execute HTTP request (for HTTP connections)"""
        if self._config.connection_type != ConnectionType.HTTP:
            raise ServiceError("execute_http_request only supports HTTP connections")

        async with self.get_connection() as session:
            async with session.request(method, url, **kwargs) as response:
                return response

    @handle_errors
    async def read_file(self, **kwargs) -> str:
        """Read from file (for file connections)"""
        if self._config.connection_type != ConnectionType.FILE:
            raise ServiceError("read_file only supports file connections")

        async with self.get_connection() as file_handle:
            return await file_handle.read(**kwargs)

    @handle_errors
    async def write_file(self, content: str, **kwargs) -> None:
        """Write to file (for file connections)"""
        if self._config.connection_type != ConnectionType.FILE:
            raise ServiceError("write_file only supports file connections")

        async with self.get_connection() as file_handle:
            await file_handle.write(content, **kwargs)
            await file_handle.flush()

    @handle_errors
    async def get_metrics(self) -> ConnectionMetrics:
        """Get current pool metrics"""
        async with self._pool_lock:
            # Update connection counts
            self._metrics.total_connections = len(self._connections)
            self._metrics.active_connections = len(self._active_connections)
            self._metrics.idle_connections = len(self._idle_queue)
            self._metrics.failed_connections = sum(
                1
                for conn in self._connections.values()
                if conn.status == ConnectionStatus.FAILED
            )

        return self._metrics

    @handle_errors
    async def get_pool_info(self) -> dict[str, Any]:
        """Get detailed pool information"""
        metrics = await self.get_metrics()

        async with self._pool_lock:
            connections_info = [
                {
                    "id": conn.connection_id,
                    "status": conn.status.value,
                    "age_seconds": conn.age_seconds,
                    "idle_time_seconds": conn.idle_time_seconds,
                    "usage_count": conn.usage_count,
                    "health_failures": conn.health_check_failures,
                }
                for conn in self._connections.values()
            ]

        return {
            "configuration": {
                "type": self._config.connection_type.value,
                "max_connections": self._config.max_connections,
                "min_connections": self._config.min_connections,
                "max_idle_time": self._config.max_idle_time,
                "health_checks_enabled": self._config.enable_health_checks,
            },
            "metrics": {
                "total_connections": metrics.total_connections,
                "active_connections": metrics.active_connections,
                "idle_connections": metrics.idle_connections,
                "failed_connections": metrics.failed_connections,
                "success_rate": metrics.success_rate,
                "utilization_rate": metrics.utilization_rate,
                "average_response_time_ms": metrics.average_response_time_ms,
            },
            "connections": connections_info,
        }

    # =============================================================================
    # Private Methods
    # =============================================================================

    def _create_factory(self) -> ConnectionFactory:
        """Create appropriate connection factory"""
        if self._config.connection_type == ConnectionType.SQLITE:
            return SQLiteConnectionFactory()
        elif self._config.connection_type == ConnectionType.HTTP:
            return HTTPConnectionFactory()
        elif self._config.connection_type == ConnectionType.FILE:
            return FileConnectionFactory()
        else:
            raise ConfigurationError(
                f"Unsupported connection type: {self._config.connection_type}"
            )

    async def _acquire_connection(self) -> PooledConnection:
        """Acquire a connection from the pool"""
        async with self._pool_lock:
            # Try to get idle connection
            while self._idle_queue:
                connection_id = self._idle_queue.popleft()
                if connection_id in self._connections:
                    pooled_conn = self._connections[connection_id]

                    # Check if connection is still healthy
                    if pooled_conn.status == ConnectionStatus.IDLE:
                        if await self._factory.health_check(pooled_conn.connection):
                            return pooled_conn
                        else:
                            # Connection failed health check, remove it
                            await self._close_connection(pooled_conn)

            # No idle connections available, create new one if under limit
            if len(self._connections) < self._config.max_connections:
                return await self._create_connection()

            # Pool is full, wait for a connection to become available
            # This should not happen with proper semaphore usage
            raise ServiceError("Connection pool exhausted")

    async def _release_connection(self, connection_id: str) -> None:
        """Release a connection back to the pool"""
        async with self._pool_lock:
            if connection_id in self._connections:
                pooled_conn = self._connections[connection_id]

                # Remove from active set
                self._active_connections.discard(connection_id)

                # Check if connection is still healthy
                if await self._factory.health_check(pooled_conn.connection):
                    pooled_conn.mark_idle()
                    self._idle_queue.append(connection_id)
                else:
                    # Connection failed, remove it
                    await self._close_connection(pooled_conn)

    async def _create_connection(self) -> PooledConnection:
        """Create a new pooled connection"""
        try:
            connection = await self._factory.create_connection(self._config)

            connection_id = f"{self._config.connection_type.value}_{len(self._connections)}_{int(time.time())}"

            pooled_conn = PooledConnection(
                connection=connection, connection_id=connection_id
            )

            async with self._pool_lock:
                self._connections[connection_id] = pooled_conn
                self._metrics.connection_creation_count += 1

            await self._logger.debug(
                "Connection created",
                {
                    "connection_id": connection_id,
                    "type": self._config.connection_type.value,
                },
            )

            return pooled_conn

        except Exception as e:
            await self._logger.error(
                "Failed to create connection",
                {"error": str(e), "type": self._config.connection_type.value},
            )
            raise

    async def _close_connection(self, pooled_conn: PooledConnection) -> None:
        """Close and remove a connection"""
        try:
            await self._factory.close_connection(pooled_conn.connection)

            async with self._pool_lock:
                # Remove from all tracking structures
                if pooled_conn.connection_id in self._connections:
                    del self._connections[pooled_conn.connection_id]

                self._active_connections.discard(pooled_conn.connection_id)

                # Remove from idle queue if present
                try:
                    self._idle_queue.remove(pooled_conn.connection_id)
                except ValueError:
                    pass

                self._metrics.connection_destruction_count += 1

            await self._logger.debug(
                "Connection closed", {"connection_id": pooled_conn.connection_id}
            )

        except Exception as e:
            await self._logger.warning(
                "Error closing connection",
                {"connection_id": pooled_conn.connection_id, "error": str(e)},
            )

    async def _health_check_loop(self) -> None:
        """Background health check loop"""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(self._config.health_check_interval)
                await self._perform_health_checks()

            except asyncio.CancelledError:
                break
            except Exception as e:
                await self._logger.error("Health check loop error", {"error": str(e)})

    async def _perform_health_checks(self) -> None:
        """Perform health checks on all connections"""
        failed_connections = []

        async with self._pool_lock:
            for pooled_conn in list(self._connections.values()):
                if pooled_conn.status != ConnectionStatus.ACTIVE:
                    try:
                        is_healthy = await self._factory.health_check(
                            pooled_conn.connection
                        )
                        if not is_healthy:
                            failed_connections.append(pooled_conn)
                    except Exception:
                        failed_connections.append(pooled_conn)

        # Close failed connections
        for pooled_conn in failed_connections:
            await self._close_connection(pooled_conn)

        if failed_connections:
            await self._logger.warning(
                "Removed unhealthy connections", {"count": len(failed_connections)}
            )

    async def _cleanup_loop(self) -> None:
        """Background cleanup loop"""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(60)  # Run every minute
                await self._cleanup_idle_connections()

            except asyncio.CancelledError:
                break
            except Exception as e:
                await self._logger.error("Cleanup loop error", {"error": str(e)})

    async def _cleanup_idle_connections(self) -> None:
        """Clean up idle connections that have exceeded max idle time"""
        expired_connections = []

        async with self._pool_lock:
            for pooled_conn in list(self._connections.values()):
                if (
                    pooled_conn.status == ConnectionStatus.IDLE
                    and pooled_conn.idle_time_seconds > self._config.max_idle_time
                    and len(self._connections) > self._config.min_connections
                ):
                    expired_connections.append(pooled_conn)

        # Close expired connections
        for pooled_conn in expired_connections:
            await self._close_connection(pooled_conn)

        if expired_connections:
            await self._logger.debug(
                "Cleaned up idle connections", {"count": len(expired_connections)}
            )


# =============================================================================
# Pool Manager for Multiple Connection Types
# =============================================================================


class ConnectionPoolManager:
    """Manages multiple connection pools"""

    def __init__(self, container: DIContainer, logger: StructuredLogger | None = None):
        """Initialize pool manager"""
        self._container = container
        self._logger = logger or StructuredLogger()
        self._pools: dict[str, ConnectionPool] = {}

    @handle_errors
    async def create_pool(self, name: str, config: ConnectionConfig) -> ConnectionPool:
        """Create and register a new connection pool"""
        if name in self._pools:
            raise ServiceError(f"Pool '{name}' already exists")

        pool = ConnectionPool(self._container, config, self._logger)
        await pool.initialize()

        self._pools[name] = pool

        await self._logger.info(
            "Connection pool created",
            {"name": name, "type": config.connection_type.value},
        )

        return pool

    @handle_errors
    async def get_pool(self, name: str) -> ConnectionPool:
        """Get connection pool by name"""
        if name not in self._pools:
            raise ServiceError(f"Pool '{name}' not found")

        return self._pools[name]

    @handle_errors
    async def shutdown_all(self) -> None:
        """Shutdown all connection pools"""
        await self._logger.info("Shutting down all connection pools")

        for name, pool in self._pools.items():
            try:
                await pool.shutdown()
            except Exception as e:
                await self._logger.error(
                    "Error shutting down pool", {"name": name, "error": str(e)}
                )

        self._pools.clear()
        await self._logger.info("All connection pools shut down")


# =============================================================================
# Global Connection Pool Manager
# =============================================================================

_global_pool_manager: ConnectionPoolManager | None = None


async def get_pool_manager() -> ConnectionPoolManager:
    """Get global connection pool manager"""
    global _global_pool_manager

    if _global_pool_manager is None:
        from .di_container import get_container

        container = get_container()
        _global_pool_manager = ConnectionPoolManager(container)

    return _global_pool_manager
