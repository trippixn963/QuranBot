# =============================================================================
# QuranBot - Lazy Loading Service
# =============================================================================
# Implements lazy loading for audio file discovery with background scanning,
# intelligent caching, and on-demand loading for optimal performance.
# =============================================================================

from abc import ABC, abstractmethod
import asyncio
from collections import defaultdict
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import wraps
from pathlib import Path
import time
from typing import Any, TypeVar
import weakref

from .cache_service import CacheService
from .di_container import DIContainer
from .exceptions import ServiceError, handle_errors
from .logger import StructuredLogger

T = TypeVar("T")


@dataclass
class LoadingState:
    """Represents the loading state of a resource"""

    is_loaded: bool = field(default=False)
    is_loading: bool = field(default=False)
    load_time: datetime | None = field(default=None)
    error: str | None = field(default=None)
    access_count: int = field(default=0)
    last_accessed: datetime | None = field(default=None)

    def mark_accessed(self) -> None:
        """Mark resource as accessed"""
        self.access_count += 1
        self.last_accessed = datetime.now(UTC)


@dataclass
class LazyLoadConfig:
    """Configuration for lazy loading"""

    background_scan_enabled: bool = field(default=True)
    background_scan_interval: int = field(default=300)  # 5 minutes
    cache_expiry_seconds: int = field(default=3600)  # 1 hour
    max_concurrent_loads: int = field(default=5)
    enable_preloading: bool = field(default=True)
    preload_popular_threshold: int = field(default=3)  # Access count
    enable_file_watching: bool = field(default=True)
    scan_depth_limit: int = field(default=10)
    memory_cache_size: int = field(default=1000)


class LazyLoadable(ABC):
    """Abstract base class for lazy-loadable resources"""

    @abstractmethod
    async def load(self) -> Any:
        """Load the resource"""
        pass

    @abstractmethod
    def get_identifier(self) -> str:
        """Get unique identifier for the resource"""
        pass

    @abstractmethod
    def get_dependencies(self) -> list[str]:
        """Get list of dependency identifiers"""
        pass


@dataclass
class AudioFileResource(LazyLoadable):
    """Represents an audio file resource for lazy loading"""

    file_path: Path
    reciter: str
    surah_number: int
    file_size: int | None = field(default=None)
    duration: float | None = field(default=None)
    metadata: dict[str, Any] = field(default_factory=dict)

    async def load(self) -> dict[str, Any]:
        """Load audio file metadata"""
        try:
            from mutagen import File

            if not self.file_path.exists():
                raise ServiceError(f"Audio file not found: {self.file_path}")

            # Get file stats
            stat = self.file_path.stat()
            self.file_size = stat.st_size

            # Load audio metadata
            audio_file = File(str(self.file_path))
            if audio_file is not None:
                self.duration = getattr(audio_file.info, "length", 0.0)

                # Extract metadata
                self.metadata = {
                    "title": (
                        audio_file.get("TIT2", [str(self.surah_number)])[0]
                        if audio_file.get("TIT2")
                        else str(self.surah_number)
                    ),
                    "artist": (
                        audio_file.get("TPE1", [self.reciter])[0]
                        if audio_file.get("TPE1")
                        else self.reciter
                    ),
                    "album": (
                        audio_file.get("TALB", ["Holy Quran"])[0]
                        if audio_file.get("TALB")
                        else "Holy Quran"
                    ),
                    "bitrate": getattr(audio_file.info, "bitrate", 0),
                    "sample_rate": getattr(audio_file.info, "sample_rate", 0),
                    "channels": getattr(audio_file.info, "channels", 0),
                }

            return {
                "file_path": str(self.file_path),
                "reciter": self.reciter,
                "surah_number": self.surah_number,
                "file_size": self.file_size,
                "duration": self.duration,
                "metadata": self.metadata,
            }

        except Exception as e:
            raise ServiceError(f"Failed to load audio file {self.file_path}: {e!s}")

    def get_identifier(self) -> str:
        """Get unique identifier"""
        return f"audio:{self.reciter}:{self.surah_number}"

    def get_dependencies(self) -> list[str]:
        """Audio files typically have no dependencies"""
        return []


@dataclass
class ReciterResource(LazyLoadable):
    """Represents a reciter directory for lazy loading"""

    reciter_path: Path
    reciter_name: str
    audio_files: list[AudioFileResource] = field(default_factory=list)
    total_files: int = field(default=0)
    total_size: int = field(default=0)

    async def load(self) -> dict[str, Any]:
        """Load reciter information and discover audio files"""
        try:
            if not self.reciter_path.exists() or not self.reciter_path.is_dir():
                raise ServiceError(f"Reciter directory not found: {self.reciter_path}")

            # Scan for audio files
            audio_extensions = {".mp3", ".wav", ".ogg", ".m4a", ".flac"}
            audio_files = []
            total_size = 0

            for file_path in self.reciter_path.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in audio_extensions:
                    # Extract surah number from filename
                    surah_number = self._extract_surah_number(file_path.name)

                    if surah_number:
                        file_size = file_path.stat().st_size
                        total_size += file_size

                        audio_resource = AudioFileResource(
                            file_path=file_path,
                            reciter=self.reciter_name,
                            surah_number=surah_number,
                            file_size=file_size,
                        )
                        audio_files.append(audio_resource)

            self.audio_files = sorted(audio_files, key=lambda x: x.surah_number)
            self.total_files = len(audio_files)
            self.total_size = total_size

            return {
                "reciter_name": self.reciter_name,
                "reciter_path": str(self.reciter_path),
                "total_files": self.total_files,
                "total_size": self.total_size,
                "audio_files": [
                    {
                        "surah_number": af.surah_number,
                        "file_path": str(af.file_path),
                        "file_size": af.file_size,
                    }
                    for af in self.audio_files
                ],
            }

        except Exception as e:
            raise ServiceError(f"Failed to load reciter {self.reciter_name}: {e!s}")

    def get_identifier(self) -> str:
        """Get unique identifier"""
        return f"reciter:{self.reciter_name}"

    def get_dependencies(self) -> list[str]:
        """Reciter depends on its audio files"""
        return [af.get_identifier() for af in self.audio_files]

    def _extract_surah_number(self, filename: str) -> int | None:
        """Extract surah number from filename"""
        import re

        # Try various patterns
        patterns = [
            r"^(\d{1,3})\..*",  # 001.mp3, 1.mp3
            r".*?(\d{1,3})\..*",  # surah_001.mp3
            r"surah[_\s-]*(\d{1,3})",  # surah_1, surah-001
            r"chapter[_\s-]*(\d{1,3})",  # chapter_1
        ]

        for pattern in patterns:
            match = re.search(pattern, filename.lower())
            if match:
                try:
                    surah_num = int(match.group(1))
                    if 1 <= surah_num <= 114:  # Valid surah range
                        return surah_num
                except ValueError:
                    continue

        return None


class LazyLoader:
    """
    High-performance lazy loading service with intelligent caching and
    background resource discovery.

    Features:
    - On-demand resource loading
    - Background scanning and preloading
    - Intelligent caching with TTL
    - Dependency management
    - File system watching
    - Memory and performance optimization
    """

    def __init__(
        self,
        container: DIContainer,
        config: LazyLoadConfig | None = None,
        cache_service: CacheService | None = None,
        logger: StructuredLogger | None = None,
    ):
        """Initialize lazy loader"""
        self._container = container
        self._config = config or LazyLoadConfig()
        self._cache_service = cache_service
        self._logger = logger or StructuredLogger()

        # Resource tracking
        self._resources: dict[str, LazyLoadable] = {}
        self._loading_states: dict[str, LoadingState] = {}
        self._dependency_graph: dict[str, set[str]] = defaultdict(set)

        # Loading management
        self._loading_semaphore = asyncio.Semaphore(self._config.max_concurrent_loads)
        self._loading_tasks: dict[str, asyncio.Task] = {}

        # Background tasks
        self._scanner_task: asyncio.Task | None = None
        self._preloader_task: asyncio.Task | None = None
        self._file_watcher_task: asyncio.Task | None = None

        # Performance tracking
        self._load_times: dict[str, float] = {}
        self._access_patterns: dict[str, list[datetime]] = defaultdict(list)

        # Thread pool for I/O operations
        self._executor = ThreadPoolExecutor(
            max_workers=3, thread_name_prefix="lazy_loader"
        )

        # Shutdown event
        self._shutdown_event = asyncio.Event()

        # Weak references for cleanup
        self._weak_refs: weakref.WeakSet = weakref.WeakSet()

    @handle_errors
    async def initialize(self) -> None:
        """Initialize the lazy loader"""
        await self._logger.info(
            "Initializing lazy loader",
            {
                "background_scan": self._config.background_scan_enabled,
                "max_concurrent_loads": self._config.max_concurrent_loads,
                "preloading_enabled": self._config.enable_preloading,
            },
        )

        # Initialize cache service if not provided
        if self._cache_service is None:
            from .cache_service import get_cache_service

            self._cache_service = await get_cache_service()

        # Start background tasks
        if self._config.background_scan_enabled:
            self._scanner_task = asyncio.create_task(self._background_scanner())

        if self._config.enable_preloading:
            self._preloader_task = asyncio.create_task(self._background_preloader())

        if self._config.enable_file_watching:
            self._file_watcher_task = asyncio.create_task(self._file_watcher())

        await self._logger.info("Lazy loader initialized successfully")

    @handle_errors
    async def shutdown(self) -> None:
        """Shutdown the lazy loader"""
        await self._logger.info("Shutting down lazy loader")

        # Signal shutdown
        self._shutdown_event.set()

        # Cancel background tasks
        for task in [self._scanner_task, self._preloader_task, self._file_watcher_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Cancel loading tasks
        for task in list(self._loading_tasks.values()):
            if not task.done():
                task.cancel()

        # Shutdown executor
        self._executor.shutdown(wait=True)

        await self._logger.info("Lazy loader shutdown complete")

    @handle_errors
    async def register_resource(self, resource: LazyLoadable) -> None:
        """Register a resource for lazy loading"""
        identifier = resource.get_identifier()
        self._resources[identifier] = resource
        self._loading_states[identifier] = LoadingState()

        # Build dependency graph
        dependencies = resource.get_dependencies()
        self._dependency_graph[identifier] = set(dependencies)

        await self._logger.debug(
            "Resource registered",
            {
                "identifier": identifier,
                "type": type(resource).__name__,
                "dependencies": len(dependencies),
            },
        )

    @handle_errors
    async def register_audio_directory(self, audio_path: Path) -> None:
        """Register all reciters and audio files in a directory"""
        if not audio_path.exists() or not audio_path.is_dir():
            raise ServiceError(f"Audio directory not found: {audio_path}")

        registered_count = 0

        # Scan for reciter directories
        for reciter_dir in audio_path.iterdir():
            if reciter_dir.is_dir():
                reciter_name = reciter_dir.name

                # Register reciter resource
                reciter_resource = ReciterResource(
                    reciter_path=reciter_dir, reciter_name=reciter_name
                )

                await self.register_resource(reciter_resource)
                registered_count += 1

        await self._logger.info(
            "Audio directory registered",
            {"path": str(audio_path), "reciters_found": registered_count},
        )

    @handle_errors
    async def load_resource(
        self, identifier: str, force_reload: bool = False
    ) -> Any | None:
        """
        Load a resource by identifier.

        Args:
            identifier: Resource identifier
            force_reload: Force reload even if cached

        Returns:
            Loaded resource data or None if not found
        """
        if identifier not in self._resources:
            await self._logger.warning("Resource not found", {"identifier": identifier})
            return None

        loading_state = self._loading_states[identifier]
        loading_state.mark_accessed()

        # Check cache first (unless force reload)
        if not force_reload and self._cache_service:
            cache_key = f"lazy_load:{identifier}"
            cached_data = await self._cache_service.get(cache_key)
            if cached_data is not None:
                loading_state.is_loaded = True
                await self._logger.debug(
                    "Resource loaded from cache", {"identifier": identifier}
                )
                return cached_data

        # Check if already loading
        if identifier in self._loading_tasks:
            await self._logger.debug(
                "Resource already loading, waiting", {"identifier": identifier}
            )
            return await self._loading_tasks[identifier]

        # Start loading
        loading_task = asyncio.create_task(self._load_resource_internal(identifier))
        self._loading_tasks[identifier] = loading_task

        try:
            result = await loading_task
            return result
        finally:
            # Clean up task
            if identifier in self._loading_tasks:
                del self._loading_tasks[identifier]

    @handle_errors
    async def load_audio_file(
        self, reciter: str, surah_number: int
    ) -> dict[str, Any] | None:
        """Load specific audio file metadata"""
        identifier = f"audio:{reciter}:{surah_number}"
        return await self.load_resource(identifier)

    @handle_errors
    async def load_reciter_info(self, reciter: str) -> dict[str, Any] | None:
        """Load reciter information and audio file list"""
        identifier = f"reciter:{reciter}"
        return await self.load_resource(identifier)

    @handle_errors
    async def get_available_reciters(self) -> list[str]:
        """Get list of available reciters"""
        reciters = []
        for identifier in self._resources:
            if identifier.startswith("reciter:"):
                reciter_name = identifier.split(":", 1)[1]
                reciters.append(reciter_name)

        return sorted(reciters)

    @handle_errors
    async def get_reciter_surahs(self, reciter: str) -> list[int]:
        """Get list of available surahs for a reciter"""
        reciter_data = await self.load_reciter_info(reciter)
        if reciter_data and "audio_files" in reciter_data:
            return [af["surah_number"] for af in reciter_data["audio_files"]]
        return []

    @handle_errors
    async def preload_popular_resources(self) -> None:
        """Preload resources based on access patterns"""
        popular_resources = []

        for identifier, state in self._loading_states.items():
            if state.access_count >= self._config.preload_popular_threshold:
                popular_resources.append(identifier)

        if popular_resources:
            await self._logger.info(
                "Preloading popular resources", {"count": len(popular_resources)}
            )

            # Load resources concurrently
            load_tasks = [
                self.load_resource(identifier) for identifier in popular_resources
            ]

            await asyncio.gather(*load_tasks, return_exceptions=True)

    @handle_errors
    async def get_loading_statistics(self) -> dict[str, Any]:
        """Get loading performance statistics"""
        total_resources = len(self._resources)
        loaded_resources = sum(
            1 for state in self._loading_states.values() if state.is_loaded
        )
        loading_resources = sum(
            1 for state in self._loading_states.values() if state.is_loading
        )

        # Calculate average load time
        avg_load_time = 0.0
        if self._load_times:
            avg_load_time = sum(self._load_times.values()) / len(self._load_times)

        # Find most accessed resources
        most_accessed = sorted(
            [(id, state.access_count) for id, state in self._loading_states.items()],
            key=lambda x: x[1],
            reverse=True,
        )[:10]

        return {
            "total_resources": total_resources,
            "loaded_resources": loaded_resources,
            "loading_resources": loading_resources,
            "load_percentage": (
                (loaded_resources / total_resources * 100) if total_resources > 0 else 0
            ),
            "average_load_time_ms": avg_load_time * 1000,
            "most_accessed_resources": most_accessed,
            "cache_hit_rate": await self._get_cache_hit_rate(),
        }

    # =============================================================================
    # Private Methods
    # =============================================================================

    async def _load_resource_internal(self, identifier: str) -> Any | None:
        """Internal resource loading with error handling and caching"""
        async with self._loading_semaphore:
            loading_state = self._loading_states[identifier]
            resource = self._resources[identifier]

            loading_state.is_loading = True
            start_time = time.time()

            try:
                # Load dependencies first
                dependencies = resource.get_dependencies()
                if dependencies:
                    dep_tasks = [
                        self.load_resource(dep_id)
                        for dep_id in dependencies
                        if dep_id in self._resources
                    ]
                    await asyncio.gather(*dep_tasks, return_exceptions=True)

                # Load resource
                await self._logger.debug("Loading resource", {"identifier": identifier})

                # Use thread pool for I/O intensive operations
                if isinstance(resource, (AudioFileResource, ReciterResource)):
                    result = await asyncio.get_event_loop().run_in_executor(
                        self._executor, lambda: asyncio.run(resource.load())
                    )
                else:
                    result = await resource.load()

                # Cache the result
                if self._cache_service and result is not None:
                    cache_key = f"lazy_load:{identifier}"
                    await self._cache_service.set(
                        cache_key, result, ttl_seconds=self._config.cache_expiry_seconds
                    )

                # Update state
                loading_state.is_loaded = True
                loading_state.load_time = datetime.now(UTC)
                loading_state.error = None

                # Track performance
                load_time = time.time() - start_time
                self._load_times[identifier] = load_time

                await self._logger.debug(
                    "Resource loaded successfully",
                    {"identifier": identifier, "load_time_ms": load_time * 1000},
                )

                return result

            except Exception as e:
                loading_state.error = str(e)
                await self._logger.error(
                    "Resource loading failed",
                    {
                        "identifier": identifier,
                        "error": str(e),
                        "load_time_ms": (time.time() - start_time) * 1000,
                    },
                )
                return None

            finally:
                loading_state.is_loading = False

    async def _background_scanner(self) -> None:
        """Background task to scan for new resources"""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(self._config.background_scan_interval)
                await self._scan_for_new_resources()

            except asyncio.CancelledError:
                break
            except Exception as e:
                await self._logger.error("Background scanner error", {"error": str(e)})

    async def _background_preloader(self) -> None:
        """Background task to preload popular resources"""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(self._config.background_scan_interval * 2)
                await self.preload_popular_resources()

            except asyncio.CancelledError:
                break
            except Exception as e:
                await self._logger.error(
                    "Background preloader error", {"error": str(e)}
                )

    async def _file_watcher(self) -> None:
        """Background task to watch for file system changes"""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(60)  # Check every minute
                # Placeholder for file system watching implementation
                # Could use watchdog library for real-time file monitoring

            except asyncio.CancelledError:
                break
            except Exception as e:
                await self._logger.error("File watcher error", {"error": str(e)})

    async def _scan_for_new_resources(self) -> None:
        """Scan for new resources in registered directories"""
        # Placeholder for scanning logic
        # Would iterate through known directories and register new resources
        pass

    async def _get_cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        if self._cache_service:
            stats = await self._cache_service.get_statistics()
            return stats.hit_rate
        return 0.0


# =============================================================================
# Decorator for Lazy Loading
# =============================================================================


def lazy_load(loader_instance: LazyLoader | None = None, cache_ttl: int = 3600):
    """
    Decorator for lazy loading function results.

    Args:
        loader_instance: Lazy loader instance (will use global if None)
        cache_ttl: Cache time-to-live in seconds
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate resource identifier
            identifier = f"func:{func.__name__}:{hash(str(args) + str(kwargs))}"

            # Get loader instance
            loader = loader_instance
            if loader is None:
                try:
                    from .di_container import get_container

                    container = get_container()
                    loader = container.get(LazyLoader)
                except:
                    # Fallback: execute function directly
                    return (
                        await func(*args, **kwargs)
                        if asyncio.iscoroutinefunction(func)
                        else func(*args, **kwargs)
                    )

            # Try to load from lazy loader
            result = await loader.load_resource(identifier)
            if result is not None:
                return result

            # Execute function and register as resource
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            # Create a simple resource for the function result
            class FunctionResource(LazyLoadable):
                def __init__(self, result_data):
                    self._result = result_data

                async def load(self):
                    return self._result

                def get_identifier(self):
                    return identifier

                def get_dependencies(self):
                    return []

            resource = FunctionResource(result)
            await loader.register_resource(resource)

            return result

        return wrapper

    return decorator


# =============================================================================
# Global Lazy Loader Access
# =============================================================================

_global_lazy_loader: LazyLoader | None = None


async def get_lazy_loader() -> LazyLoader:
    """Get global lazy loader instance"""
    global _global_lazy_loader

    if _global_lazy_loader is None:
        from .di_container import get_container

        container = get_container()
        _global_lazy_loader = LazyLoader(container)
        await _global_lazy_loader.initialize()

    return _global_lazy_loader
