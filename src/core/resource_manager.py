# =============================================================================
# QuranBot - Resource Manager
# =============================================================================
# Comprehensive resource management and cleanup service with graceful shutdown,
# resource tracking, leak prevention, and dependency management.
# =============================================================================

from abc import ABC, abstractmethod
import asyncio
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
import signal
import time
from typing import Any, TypeVar
import weakref

import psutil

from .di_container import DIContainer
from .exceptions import ServiceError
from .structured_logger import StructuredLogger

T = TypeVar("T")


class ResourceType(str, Enum):
    """Types of resources managed"""

    TASK = "task"
    CONNECTION = "connection"
    FILE_HANDLE = "file_handle"
    NETWORK_SESSION = "network_session"
    CACHE = "cache"
    DATABASE = "database"
    THREAD_POOL = "thread_pool"
    PROCESS_POOL = "process_pool"
    TEMPORARY_FILE = "temporary_file"
    MEMORY_BUFFER = "memory_buffer"
    SERVICE = "service"


class ResourceState(str, Enum):
    """Resource lifecycle states"""

    CREATING = "creating"
    ACTIVE = "active"
    IDLE = "idle"
    CLEANING_UP = "cleaning_up"
    CLEANED = "cleaned"
    FAILED = "failed"


class ShutdownPhase(str, Enum):
    """Shutdown phases for ordered cleanup"""

    STOP_ACCEPTING_NEW = "stop_accepting_new"
    DRAIN_PENDING = "drain_pending"
    CLEANUP_SERVICES = "cleanup_services"
    CLEANUP_CONNECTIONS = "cleanup_connections"
    CLEANUP_FILES = "cleanup_files"
    CLEANUP_MEMORY = "cleanup_memory"
    FINAL_CLEANUP = "final_cleanup"


@dataclass
class ResourceInfo:
    """Information about a managed resource"""

    resource_id: str
    resource_type: ResourceType
    resource: Any
    state: ResourceState = field(default=ResourceState.CREATING)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_accessed: datetime = field(default_factory=lambda: datetime.now(UTC))
    cleanup_callbacks: list[Callable] = field(default_factory=list)
    dependencies: set[str] = field(default_factory=set)
    dependents: set[str] = field(default_factory=set)
    metadata: dict[str, Any] = field(default_factory=dict)
    cleanup_timeout: float = field(default=30.0)
    memory_usage_bytes: int = field(default=0)

    @property
    def age_seconds(self) -> float:
        """Get resource age in seconds"""
        return (datetime.now(UTC) - self.created_at).total_seconds()

    @property
    def idle_time_seconds(self) -> float:
        """Get idle time in seconds"""
        return (datetime.now(UTC) - self.last_accessed).total_seconds()

    def mark_accessed(self) -> None:
        """Mark resource as accessed"""
        self.last_accessed = datetime.now(UTC)
        if self.state == ResourceState.IDLE:
            self.state = ResourceState.ACTIVE


@dataclass
class CleanupTask:
    """Represents a cleanup task with priority and dependencies"""

    resource_id: str
    cleanup_func: Callable
    priority: int = field(default=100)  # Lower number = higher priority
    phase: ShutdownPhase = field(default=ShutdownPhase.CLEANUP_SERVICES)
    timeout: float = field(default=30.0)
    dependencies: set[str] = field(default_factory=set)

    def __lt__(self, other: "CleanupTask") -> bool:
        """Compare cleanup tasks by priority"""
        return self.priority < other.priority


@dataclass
class ResourceStats:
    """Resource usage statistics"""

    total_resources: int = field(default=0)
    active_resources: int = field(default=0)
    idle_resources: int = field(default=0)
    failed_resources: int = field(default=0)
    memory_usage_mb: float = field(default=0.0)
    cpu_usage_percent: float = field(default=0.0)
    open_file_descriptors: int = field(default=0)
    active_tasks: int = field(default=0)
    active_connections: int = field(default=0)
    cleanup_operations: int = field(default=0)
    resource_leaks_detected: int = field(default=0)


class ManagedResource(ABC):
    """Abstract base class for managed resources"""

    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup the resource"""
        pass

    @abstractmethod
    def get_resource_type(self) -> ResourceType:
        """Get the resource type"""
        pass

    @abstractmethod
    def get_memory_usage(self) -> int:
        """Get estimated memory usage in bytes"""
        pass


class ResourceManager:
    """
    Comprehensive resource management service with graceful shutdown,
    dependency tracking, and leak prevention.

    Features:
    - Automatic resource tracking and cleanup
    - Dependency-aware shutdown ordering
    - Graceful degradation during shutdown
    - Resource leak detection and prevention
    - Memory and performance monitoring
    - Signal handling for clean shutdown
    - Resource lifecycle management
    """

    def __init__(self, container: DIContainer, logger: StructuredLogger | None = None):
        """Initialize resource manager"""
        self._container = container
        self._logger = logger or StructuredLogger()

        # Resource tracking
        self._resources: dict[str, ResourceInfo] = {}
        self._resource_types: dict[ResourceType, set[str]] = defaultdict(set)
        self._cleanup_tasks: dict[str, CleanupTask] = {}

        # Shutdown management
        self._shutdown_event = asyncio.Event()
        self._shutdown_in_progress = False
        self._shutdown_phase = None
        self._emergency_shutdown = False

        # Performance monitoring
        self._stats = ResourceStats()
        self._process = psutil.Process()
        self._monitoring_task: asyncio.Task | None = None

        # Cleanup tracking
        self._cleanup_order: list[str] = []
        self._cleanup_semaphore = asyncio.Semaphore(10)  # Max concurrent cleanups

        # Signal handlers
        self._signal_handlers_installed = False

        # Weak references for automatic cleanup
        self._weak_refs: weakref.WeakSet = weakref.WeakSet()

        # Lock for thread safety
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize the resource manager"""
        await self._logger.info("Initializing resource manager")

        # Note: Signal handlers are installed in main.py to avoid conflicts
        # await self._install_signal_handlers()

        # Start monitoring
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())

        await self._logger.info("Resource manager initialized successfully")

    async def register_resource(
        self,
        resource: Any,
        resource_type: ResourceType,
        resource_id: str | None = None,
        cleanup_callbacks: list[Callable] | None = None,
        dependencies: set[str] | None = None,
        cleanup_timeout: float = 30.0,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Register a resource for management.

        Args:
            resource: The resource to manage
            resource_type: Type of resource
            resource_id: Unique identifier (auto-generated if None)
            cleanup_callbacks: List of cleanup functions
            dependencies: Resource IDs this resource depends on
            cleanup_timeout: Timeout for cleanup operations
            metadata: Additional metadata

        Returns:
            Resource ID
        """
        async with self._lock:
            if resource_id is None:
                resource_id = f"{resource_type.value}_{id(resource)}_{int(time.time())}"

            if resource_id in self._resources:
                raise ServiceError(f"Resource '{resource_id}' already registered")

            # Calculate memory usage
            memory_usage = 0
            if isinstance(resource, ManagedResource):
                memory_usage = resource.get_memory_usage()
            else:
                memory_usage = self._estimate_memory_usage(resource)

            # Create resource info
            resource_info = ResourceInfo(
                resource_id=resource_id,
                resource_type=resource_type,
                resource=resource,
                cleanup_callbacks=cleanup_callbacks or [],
                dependencies=dependencies or set(),
                cleanup_timeout=cleanup_timeout,
                metadata=metadata or {},
                memory_usage_bytes=memory_usage,
            )

            # Register resource
            self._resources[resource_id] = resource_info
            self._resource_types[resource_type].add(resource_id)

            # Update dependencies
            for dep_id in resource_info.dependencies:
                if dep_id in self._resources:
                    self._resources[dep_id].dependents.add(resource_id)

            # Add to weak references if applicable
            try:
                self._weak_refs.add(resource)
            except TypeError:
                pass  # Not all objects support weak references

            resource_info.state = ResourceState.ACTIVE

            await self._logger.debug(
                "Resource registered",
                {
                    "resource_id": resource_id,
                    "type": resource_type.value,
                    "dependencies": len(resource_info.dependencies),
                    "memory_usage_bytes": memory_usage,
                },
            )

            return resource_id

    async def unregister_resource(
        self, resource_id: str, force_cleanup: bool = False
    ) -> bool:
        """
        Unregister and cleanup a resource.

        Args:
            resource_id: Resource to unregister
            force_cleanup: Force cleanup even if dependencies exist

        Returns:
            True if successfully unregistered
        """
        async with self._lock:
            if resource_id not in self._resources:
                return False

            resource_info = self._resources[resource_id]

            # Check for dependents
            if resource_info.dependents and not force_cleanup:
                await self._logger.warning(
                    "Cannot cleanup resource with active dependents",
                    {
                        "resource_id": resource_id,
                        "dependents": list(resource_info.dependents),
                    },
                )
                return False

            # Cleanup dependents first if force cleanup
            if force_cleanup:
                for dependent_id in list(resource_info.dependents):
                    await self.unregister_resource(dependent_id, force_cleanup=True)

            # Perform cleanup
            success = await self._cleanup_resource(resource_info)

            if success:
                # Remove from tracking
                del self._resources[resource_id]
                self._resource_types[resource_info.resource_type].discard(resource_id)

                # Update dependencies
                for dep_id in resource_info.dependencies:
                    if dep_id in self._resources:
                        self._resources[dep_id].dependents.discard(resource_id)

            return success

    async def get_resource(self, resource_id: str) -> Any | None:
        """Get a managed resource by ID"""
        if resource_id in self._resources:
            resource_info = self._resources[resource_id]
            resource_info.mark_accessed()
            return resource_info.resource
        return None

    async def mark_resource_idle(self, resource_id: str) -> None:
        """Mark a resource as idle"""
        if resource_id in self._resources:
            self._resources[resource_id].state = ResourceState.IDLE

    async def get_resource_info(self, resource_id: str) -> ResourceInfo | None:
        """Get detailed information about a resource"""
        return self._resources.get(resource_id)

    async def list_resources(
        self,
        resource_type: ResourceType | None = None,
        state: ResourceState | None = None,
    ) -> list[ResourceInfo]:
        """List managed resources with optional filtering"""
        resources = []

        for resource_info in self._resources.values():
            if resource_type and resource_info.resource_type != resource_type:
                continue
            if state and resource_info.state != state:
                continue
            resources.append(resource_info)

        return resources

    async def initiate_shutdown(
        self, timeout: float = 60.0, emergency: bool = False
    ) -> None:
        """
        Initiate graceful shutdown of all resources.

        Args:
            timeout: Total shutdown timeout
            emergency: Emergency shutdown (skip graceful phases)
        """
        if self._shutdown_in_progress:
            await self._logger.warning("Shutdown already in progress")
            return

        self._shutdown_in_progress = True
        self._emergency_shutdown = emergency
        self._shutdown_event.set()

        await self._logger.info(
            "Initiating resource cleanup",
            {
                "emergency": emergency,
                "timeout": timeout,
                "total_resources": len(self._resources),
            },
        )

        start_time = time.time()

        try:
            if emergency:
                await self._emergency_cleanup(timeout)
            else:
                await self._graceful_shutdown(timeout)

            cleanup_time = time.time() - start_time
            await self._logger.info(
                "Resource cleanup completed",
                {
                    "cleanup_time_seconds": cleanup_time,
                    "remaining_resources": len(self._resources),
                },
            )

        except TimeoutError:
            await self._logger.error(
                "Resource cleanup timed out",
                {"timeout": timeout, "remaining_resources": len(self._resources)},
            )
            # Force emergency cleanup
            await self._emergency_cleanup(5.0)

        except Exception as e:
            await self._logger.error(
                "Error during resource cleanup",
                {"error": str(e), "remaining_resources": len(self._resources)},
            )

    async def get_statistics(self) -> ResourceStats:
        """Get current resource usage statistics"""
        async with self._lock:
            # Count resources by state
            active_count = sum(
                1 for r in self._resources.values() if r.state == ResourceState.ACTIVE
            )
            idle_count = sum(
                1 for r in self._resources.values() if r.state == ResourceState.IDLE
            )
            failed_count = sum(
                1 for r in self._resources.values() if r.state == ResourceState.FAILED
            )

            # Calculate memory usage
            total_memory = sum(r.memory_usage_bytes for r in self._resources.values())

            # Get system stats
            try:
                cpu_percent = self._process.cpu_percent()
                memory_info = self._process.memory_info()
                open_fds = len(self._process.open_files())
            except Exception:
                cpu_percent = 0.0
                open_fds = 0

            # Count specific resource types
            task_count = len(self._resource_types[ResourceType.TASK])
            connection_count = len(self._resource_types[ResourceType.CONNECTION])

            self._stats = ResourceStats(
                total_resources=len(self._resources),
                active_resources=active_count,
                idle_resources=idle_count,
                failed_resources=failed_count,
                memory_usage_mb=total_memory / (1024 * 1024),
                cpu_usage_percent=cpu_percent,
                open_file_descriptors=open_fds,
                active_tasks=task_count,
                active_connections=connection_count,
            )

            return self._stats

    async def detect_resource_leaks(self) -> list[dict[str, Any]]:
        """Detect potential resource leaks"""
        leaks = []
        current_time = datetime.now(UTC)

        for resource_info in self._resources.values():
            # Check for long-running idle resources
            if (
                resource_info.state == ResourceState.IDLE
                and resource_info.idle_time_seconds > 3600
            ):  # 1 hour
                leaks.append(
                    {
                        "type": "idle_resource",
                        "resource_id": resource_info.resource_id,
                        "resource_type": resource_info.resource_type.value,
                        "idle_time_seconds": resource_info.idle_time_seconds,
                        "memory_usage_bytes": resource_info.memory_usage_bytes,
                    }
                )

            # Check for very old resources
            if resource_info.age_seconds > 24 * 3600:  # 24 hours
                leaks.append(
                    {
                        "type": "old_resource",
                        "resource_id": resource_info.resource_id,
                        "resource_type": resource_info.resource_type.value,
                        "age_seconds": resource_info.age_seconds,
                        "last_accessed": resource_info.last_accessed.isoformat(),
                    }
                )

        # Check for circular dependencies
        circular_deps = await self._detect_circular_dependencies()
        for cycle in circular_deps:
            leaks.append({"type": "circular_dependency", "resource_cycle": cycle})

        if leaks:
            self._stats.resource_leaks_detected = len(leaks)
            await self._logger.warning(
                "Resource leaks detected", {"leak_count": len(leaks)}
            )

        return leaks

    # =============================================================================
    # Private Methods
    # =============================================================================

    async def _graceful_shutdown(self, timeout: float) -> None:
        """Perform graceful shutdown in phases"""
        phase_timeout = timeout / len(ShutdownPhase)

        for phase in ShutdownPhase:
            self._shutdown_phase = phase
            await self._logger.info(f"Shutdown phase: {phase.value}")

            start_time = time.time()

            try:
                await asyncio.wait_for(
                    self._execute_shutdown_phase(phase), timeout=phase_timeout
                )
            except TimeoutError:
                await self._logger.warning(f"Phase {phase.value} timed out")
                # Continue to next phase

            phase_time = time.time() - start_time
            await self._logger.debug(
                f"Phase {phase.value} completed", {"phase_time_seconds": phase_time}
            )

    async def _execute_shutdown_phase(self, phase: ShutdownPhase) -> None:
        """Execute a specific shutdown phase"""
        if phase == ShutdownPhase.STOP_ACCEPTING_NEW:
            # Stop accepting new resources
            # This would involve disabling resource creation
            pass

        elif phase == ShutdownPhase.DRAIN_PENDING:
            # Wait for pending operations to complete
            await self._drain_pending_operations()

        elif phase == ShutdownPhase.CLEANUP_SERVICES:
            # Cleanup service-type resources
            await self._cleanup_resources_by_type(ResourceType.SERVICE)

        elif phase == ShutdownPhase.CLEANUP_CONNECTIONS:
            # Cleanup connection resources
            await self._cleanup_resources_by_type(ResourceType.CONNECTION)
            await self._cleanup_resources_by_type(ResourceType.NETWORK_SESSION)

        elif phase == ShutdownPhase.CLEANUP_FILES:
            # Cleanup file resources
            await self._cleanup_resources_by_type(ResourceType.FILE_HANDLE)
            await self._cleanup_resources_by_type(ResourceType.TEMPORARY_FILE)

        elif phase == ShutdownPhase.CLEANUP_MEMORY:
            # Cleanup memory resources
            await self._cleanup_resources_by_type(ResourceType.CACHE)
            await self._cleanup_resources_by_type(ResourceType.MEMORY_BUFFER)

        elif phase == ShutdownPhase.FINAL_CLEANUP:
            # Final cleanup of remaining resources
            await self._cleanup_all_remaining_resources()

    async def _emergency_cleanup(self, timeout: float) -> None:
        """Perform emergency cleanup of all resources"""
        await self._logger.warning("Performing emergency cleanup")

        # Cancel all tasks immediately
        await self._cancel_all_tasks()

        # Cleanup all resources in parallel with timeout
        cleanup_tasks = []
        for resource_id in list(self._resources.keys()):
            task = asyncio.create_task(
                self._cleanup_resource_with_timeout(resource_id, 5.0)
            )
            cleanup_tasks.append(task)

        if cleanup_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*cleanup_tasks, return_exceptions=True),
                    timeout=timeout,
                )
            except TimeoutError:
                await self._logger.error("Emergency cleanup timed out")

    async def _cleanup_resources_by_type(self, resource_type: ResourceType) -> None:
        """Cleanup all resources of a specific type"""
        resource_ids = list(self._resource_types[resource_type])

        if not resource_ids:
            return

        await self._logger.debug(
            f"Cleaning up {resource_type.value} resources", {"count": len(resource_ids)}
        )

        # Sort by dependency order
        sorted_ids = await self._sort_by_dependencies(resource_ids)

        # Cleanup in order
        for resource_id in sorted_ids:
            if resource_id in self._resources:
                await self.unregister_resource(resource_id, force_cleanup=True)

    async def _cleanup_all_remaining_resources(self) -> None:
        """Cleanup all remaining resources"""
        remaining_ids = list(self._resources.keys())

        if not remaining_ids:
            return

        await self._logger.debug(
            "Cleaning up remaining resources", {"count": len(remaining_ids)}
        )

        # Sort by dependency order
        sorted_ids = await self._sort_by_dependencies(remaining_ids)

        # Cleanup in parallel batches
        batch_size = 5
        for i in range(0, len(sorted_ids), batch_size):
            batch = sorted_ids[i : i + batch_size]

            cleanup_tasks = [
                self._cleanup_resource_with_timeout(resource_id, 10.0)
                for resource_id in batch
                if resource_id in self._resources
            ]

            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)

    async def _cleanup_resource(self, resource_info: ResourceInfo) -> bool:
        """Cleanup a single resource"""
        resource_info.state = ResourceState.CLEANING_UP

        try:
            # Call custom cleanup callbacks first
            for callback in resource_info.cleanup_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback()
                    else:
                        callback()
                except Exception as e:
                    await self._logger.warning(
                        "Cleanup callback failed",
                        {"resource_id": resource_info.resource_id, "error": str(e)},
                    )

            # Call resource-specific cleanup
            if isinstance(resource_info.resource, ManagedResource):
                await resource_info.resource.cleanup()
            elif hasattr(resource_info.resource, "close"):
                if asyncio.iscoroutinefunction(resource_info.resource.close):
                    await resource_info.resource.close()
                else:
                    resource_info.resource.close()
            elif hasattr(resource_info.resource, "shutdown"):
                if asyncio.iscoroutinefunction(resource_info.resource.shutdown):
                    await resource_info.resource.shutdown()
                else:
                    resource_info.resource.shutdown()

            resource_info.state = ResourceState.CLEANED
            self._stats.cleanup_operations += 1

            await self._logger.debug(
                "Resource cleaned up successfully",
                {
                    "resource_id": resource_info.resource_id,
                    "type": resource_info.resource_type.value,
                },
            )

            return True

        except Exception as e:
            resource_info.state = ResourceState.FAILED
            await self._logger.error(
                "Resource cleanup failed",
                {"resource_id": resource_info.resource_id, "error": str(e)},
            )
            return False

    async def _cleanup_resource_with_timeout(
        self, resource_id: str, timeout: float
    ) -> bool:
        """Cleanup resource with timeout"""
        if resource_id not in self._resources:
            return True

        resource_info = self._resources[resource_id]

        try:
            return await asyncio.wait_for(
                self._cleanup_resource(resource_info), timeout=timeout
            )
        except TimeoutError:
            await self._logger.error(
                "Resource cleanup timed out",
                {"resource_id": resource_id, "timeout": timeout},
            )
            resource_info.state = ResourceState.FAILED
            return False

    async def _sort_by_dependencies(self, resource_ids: list[str]) -> list[str]:
        """Sort resources by dependency order (dependents first)"""
        # Simple topological sort
        sorted_ids = []
        remaining = set(resource_ids)

        while remaining:
            # Find resources with no dependents in remaining set
            candidates = []
            for resource_id in remaining:
                resource_info = self._resources.get(resource_id)
                if resource_info:
                    dependents_in_remaining = resource_info.dependents & remaining
                    if not dependents_in_remaining:
                        candidates.append(resource_id)

            if not candidates:
                # Circular dependency or error, add remaining arbitrarily
                candidates = list(remaining)

            # Add candidates to sorted list
            for resource_id in candidates:
                sorted_ids.append(resource_id)
                remaining.discard(resource_id)

        return sorted_ids

    async def _detect_circular_dependencies(self) -> list[list[str]]:
        """Detect circular dependencies in resource graph"""
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(resource_id: str, path: list[str]) -> None:
            if resource_id in rec_stack:
                # Found cycle
                cycle_start = path.index(resource_id)
                cycle = path[cycle_start:] + [resource_id]
                cycles.append(cycle)
                return

            if resource_id in visited:
                return

            visited.add(resource_id)
            rec_stack.add(resource_id)

            resource_info = self._resources.get(resource_id)
            if resource_info:
                for dep_id in resource_info.dependencies:
                    if dep_id in self._resources:
                        dfs(dep_id, path + [resource_id])

            rec_stack.discard(resource_id)

        for resource_id in self._resources:
            if resource_id not in visited:
                dfs(resource_id, [])

        return cycles

    async def _cancel_all_tasks(self) -> None:
        """Cancel all asyncio tasks"""
        task_resources = self._resource_types[ResourceType.TASK]

        for resource_id in list(task_resources):
            resource_info = self._resources.get(resource_id)
            if resource_info and isinstance(resource_info.resource, asyncio.Task):
                task = resource_info.resource
                if not task.done():
                    task.cancel()

    async def _drain_pending_operations(self) -> None:
        """Wait for pending operations to complete"""
        # Wait for active tasks to complete
        active_tasks = []
        for resource_id in self._resource_types[ResourceType.TASK]:
            resource_info = self._resources.get(resource_id)
            if (
                resource_info
                and isinstance(resource_info.resource, asyncio.Task)
                and not resource_info.resource.done()
            ):
                active_tasks.append(resource_info.resource)

        if active_tasks:
            await self._logger.info(
                "Waiting for active tasks to complete",
                {"task_count": len(active_tasks)},
            )

            try:
                await asyncio.wait_for(
                    asyncio.gather(*active_tasks, return_exceptions=True), timeout=30.0
                )
            except TimeoutError:
                await self._logger.warning("Some tasks did not complete in time")

    async def _monitoring_loop(self) -> None:
        """Background monitoring loop"""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(30)  # Monitor every 30 seconds

                # Update statistics
                await self.get_statistics()

                # Check for resource leaks
                leaks = await self.detect_resource_leaks()

                # Log resource usage periodically
                if self._stats.total_resources > 0:
                    await self._logger.debug(
                        "Resource usage",
                        {
                            "total_resources": self._stats.total_resources,
                            "memory_usage_mb": self._stats.memory_usage_mb,
                            "cpu_usage_percent": self._stats.cpu_usage_percent,
                            "leaks_detected": len(leaks),
                        },
                    )

            except asyncio.CancelledError:
                break
            except Exception as e:
                await self._logger.error("Monitoring loop error", {"error": str(e)})

    async def _install_signal_handlers(self) -> None:
        """Install signal handlers for graceful shutdown"""
        if self._signal_handlers_installed:
            return

        def signal_handler(signum, frame):
            asyncio.create_task(self.initiate_shutdown(timeout=30.0))

        try:
            signal.signal(signal.SIGTERM, signal_handler)
            signal.signal(signal.SIGINT, signal_handler)
            self._signal_handlers_installed = True

            await self._logger.debug("Signal handlers installed")
        except Exception as e:
            await self._logger.warning(
                "Could not install signal handlers", {"error": str(e)}
            )

    def _estimate_memory_usage(self, resource: Any) -> int:
        """Estimate memory usage of a resource"""
        try:
            import sys

            return sys.getsizeof(resource)
        except Exception:
            return 0


# =============================================================================
# Global Resource Manager
# =============================================================================

_global_resource_manager: ResourceManager | None = None


async def get_resource_manager() -> ResourceManager:
    """Get global resource manager instance"""
    global _global_resource_manager

    if _global_resource_manager is None:
        from .di_container import get_container

        container = get_container()
        _global_resource_manager = ResourceManager(container)
        await _global_resource_manager.initialize()

    return _global_resource_manager


# =============================================================================
# Decorator for Automatic Resource Management
# =============================================================================


def managed_resource(
    resource_type: ResourceType,
    cleanup_timeout: float = 30.0,
    auto_cleanup: bool = True,
):
    """
    Decorator for automatic resource management.

    Args:
        resource_type: Type of resource
        cleanup_timeout: Cleanup timeout
        auto_cleanup: Whether to auto-cleanup on function exit
    """

    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            resource_manager = await get_resource_manager()

            if asyncio.iscoroutinefunction(func):
                resource = await func(*args, **kwargs)
            else:
                resource = func(*args, **kwargs)

            # Register resource
            resource_id = await resource_manager.register_resource(
                resource=resource,
                resource_type=resource_type,
                cleanup_timeout=cleanup_timeout,
            )

            try:
                return resource
            finally:
                if auto_cleanup:
                    await resource_manager.unregister_resource(resource_id)

        return wrapper

    return decorator
