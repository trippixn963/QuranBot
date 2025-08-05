# =============================================================================
# QuranBot - Metadata Cache Service
# =============================================================================
# Caches audio file metadata and reciter information for fast access.
# Provides efficient lookup for audio files and Quran data with performance monitoring.
# Designed for high-performance audio file operations with intelligent caching.
# =============================================================================

import asyncio
import hashlib
import json
import subprocess
import sys
import time
from collections import OrderedDict, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from mutagen.mp3 import MP3

from ...config import ReciterName, get_config
from ...config.timezone import APP_TIMEZONE
from ...core.errors import BotError, ServiceError
from ...core.logger import TreeLogger, log_event
from ...data.models import AudioFileInfo, AudioQuality, ReciterInfo, SurahInfo
from ..core.base_service import BaseService


class MetadataCache(BaseService):
    """
    Metadata cache service for audio and Quran data.

    Provides high-performance caching with intelligent preloading,
    memory management, and comprehensive performance monitoring.
    """

    def __init__(self):
        super().__init__("MetadataCache")

        self.config = get_config()
        self.cache_dir = self.config.data_folder / "cache"
        self.cache_file = self.cache_dir / "metadata_cache.json"

        # Cache storage
        self.audio_metadata_cache: Dict[str, AudioFileInfo] = {}
        self.reciter_cache: Dict[str, ReciterInfo] = {}
        self.surah_cache: Dict[int, SurahInfo] = {}
        self.file_hash_cache: Dict[str, str] = {}

        # LRU cache for frequently accessed items
        self.lru_cache: OrderedDict = OrderedDict()
        self.max_lru_size = 1000

        # Cache statistics
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "preloads": 0,
            "cache_builds": 0,
            "memory_cleanups": 0,
            "total_requests": 0,
            "average_lookup_time": 0.0,
            "cache_size_mb": 0.0,
            "hit_rate": 0.0,
        }

        # Performance tracking
        self.lookup_times: List[float] = []
        self.max_lookup_history = 1000

        # Cache configuration
        self.enable_preloading = True
        self.enable_file_watching = True
        self.cache_ttl_hours = 24
        self.memory_limit_mb = 100
        self.auto_cleanup_interval = 300  # 5 minutes

        # Background tasks
        self.cleanup_task: Optional[asyncio.Task] = None
        self.file_watcher_task: Optional[asyncio.Task] = None

        # File system monitoring
        self.watched_directories: Set[Path] = set()
        self.last_scan_time: Optional[datetime] = None
        self.file_modification_times: Dict[str, float] = {}

        TreeLogger.info(
            "🗂️ Metadata Cache Configuration",
            {
                "cache_directory": str(self.cache_dir),
                "max_lru_size": self.max_lru_size,
                "memory_limit_mb": f"{self.memory_limit_mb} MB",
                "cache_ttl": f"{self.cache_ttl_hours}h",
                "preloading": "✅ Enabled" if self.enable_preloading else "❌ Disabled",
                "file_watching": (
                    "✅ Enabled" if self.enable_file_watching else "❌ Disabled"
                ),
                "cleanup_interval": f"{self.auto_cleanup_interval}s",
            },
        )

    async def _initialize(self) -> None:
        """Initialize metadata cache with comprehensive setup."""
        TreeLogger.info("Initializing metadata cache service", service="system")

        try:
            # Ensure cache directory exists
            await self._ensure_cache_directory()

            # Load existing cache if available
            await self._load_cache_from_disk()

            # Initialize Surah metadata
            await self._initialize_surah_metadata()

            # Scan and cache audio files
            if self.enable_preloading:
                await self._preload_audio_metadata()

            # Setup file system monitoring
            if self.enable_file_watching:
                await self._setup_file_watching()

            # Calculate initial memory usage
            await self._calculate_memory_usage()

            TreeLogger.success(
                "Metadata cache initialized",
                {
                    "audio_files_cached": len(self.audio_metadata_cache),
                    "reciters_cached": len(self.reciter_cache),
                    "surahs_cached": len(self.surah_cache),
                    "memory_usage_mb": f"{self.cache_stats['cache_size_mb']:.2f}",
                    "preloading": (
                        "✅ Complete" if self.enable_preloading else "⏭️ Skipped"
                    ),
                    "file_watching": (
                        "✅ Active" if self.enable_file_watching else "❌ Disabled"
                    ),
                },
            )

        except Exception as e:
            log_event(
                "ERROR",
                "Metadata cache initialization failed",
                {"error": str(e), "cache_dir": str(self.cache_dir)},
            )
            raise ServiceError(
                f"Failed to initialize metadata cache: {e}",
                service_name="MetadataCache",
            )

    async def _start(self) -> None:
        """Start metadata cache with background tasks."""
        TreeLogger.info("Starting metadata cache service", service="system")

        try:
            # Start background cleanup task
            await self._start_cleanup_task()

            # Start file watcher task
            if self.enable_file_watching:
                await self._start_file_watcher_task()

            # Log startup statistics
            await self._log_startup_statistics()

            TreeLogger.success(
                "Metadata cache started",
                {
                    "cleanup_task": "✅ Running",
                    "file_watcher": (
                        "✅ Running" if self.enable_file_watching else "❌ Disabled"
                    ),
                    "cache_entries": len(self.audio_metadata_cache),
                    "hit_rate": f"{self._calculate_hit_rate():.1f}%",
                },
            )

        except Exception as e:
            TreeLogger.error("Metadata cache start failed", None, {"error": str(e)})
            raise ServiceError(
                f"Failed to start metadata cache: {e}", service_name="MetadataCache"
            )

    async def _stop(self) -> None:
        """Stop metadata cache gracefully."""
        TreeLogger.info("Stopping metadata cache service", service="system")

        try:
            # Stop background tasks
            await self._stop_background_tasks()

            # Save cache to disk
            await self._save_cache_to_disk()

            # Log final statistics
            await self._log_final_statistics()

            TreeLogger.success(
                "Metadata cache stopped",
                {
                    "cache_saved": "✅ Complete",
                    "total_hits": self.cache_stats["hits"],
                    "total_misses": self.cache_stats["misses"],
                    "final_hit_rate": f"{self._calculate_hit_rate():.1f}%",
                },
            )

        except Exception as e:
            TreeLogger.error(
                "Error during metadata cache stop", None, {"error": str(e)}
            )

    async def _cleanup(self) -> None:
        """Clean up metadata cache resources."""
        TreeLogger.info("Cleaning up metadata cache service", service="system")

        try:
            # Clear all caches
            self.audio_metadata_cache.clear()
            self.reciter_cache.clear()
            self.surah_cache.clear()
            self.file_hash_cache.clear()
            self.lru_cache.clear()

            # Clear performance tracking
            self.lookup_times.clear()
            self.file_modification_times.clear()
            self.watched_directories.clear()

            # Reset statistics
            self.cache_stats = {
                "hits": 0,
                "misses": 0,
                "evictions": 0,
                "preloads": 0,
                "cache_builds": 0,
                "memory_cleanups": 0,
                "total_requests": 0,
                "average_lookup_time": 0.0,
                "cache_size_mb": 0.0,
                "hit_rate": 0.0,
            }

            TreeLogger.success(
                "Metadata cache cleanup complete",
                {
                    "caches": "✅ Cleared",
                    "statistics": "✅ Reset",
                    "memory": "✅ Released",
                },
                service="system",
            )

        except Exception as e:
            TreeLogger.error("Metadata cache cleanup error", None, {"error": str(e)})

    async def _health_check(self) -> Dict[str, Any]:
        """Comprehensive metadata cache health check."""
        health_data = {
            "service_name": "MetadataCache",
            "cache_status": "unknown",
            "cache_statistics": self.cache_stats.copy(),
            "cache_sizes": {},
            "performance_metrics": {},
            "background_tasks": {},
            "memory_usage": {},
            "file_system": {},
        }

        try:
            # Cache status
            total_entries = (
                len(self.audio_metadata_cache)
                + len(self.reciter_cache)
                + len(self.surah_cache)
            )

            if total_entries > 0:
                health_data["cache_status"] = "healthy"
            else:
                health_data["cache_status"] = "empty"

            # Cache sizes
            health_data["cache_sizes"] = {
                "audio_metadata": len(self.audio_metadata_cache),
                "reciters": len(self.reciter_cache),
                "surahs": len(self.surah_cache),
                "file_hashes": len(self.file_hash_cache),
                "lru_cache": len(self.lru_cache),
            }

            # Performance metrics
            health_data["performance_metrics"] = {
                "hit_rate": f"{self._calculate_hit_rate():.1f}%",
                "average_lookup_ms": f"{self.cache_stats['average_lookup_time'] * 1000:.2f}",
                "total_requests": self.cache_stats["total_requests"],
                "memory_usage_mb": f"{self.cache_stats['cache_size_mb']:.2f}",
            }

            # Background tasks
            health_data["background_tasks"] = {
                "cleanup": (
                    "running"
                    if self.cleanup_task and not self.cleanup_task.done()
                    else "stopped"
                ),
                "file_watcher": (
                    "running"
                    if self.file_watcher_task and not self.file_watcher_task.done()
                    else "stopped"
                ),
            }

            # Memory usage
            health_data["memory_usage"] = {
                "current_mb": self.cache_stats["cache_size_mb"],
                "limit_mb": self.memory_limit_mb,
                "usage_percentage": f"{(self.cache_stats['cache_size_mb'] / self.memory_limit_mb) * 100:.1f}%",
            }

            # File system
            health_data["file_system"] = {
                "cache_file_exists": self.cache_file.exists(),
                "watched_directories": len(self.watched_directories),
                "last_scan": (
                    self.last_scan_time.isoformat() if self.last_scan_time else None
                ),
            }

        except Exception as e:
            TreeLogger.error("Cache health check failed", None, {"error": str(e)})
            health_data["cache_status"] = "error"
            health_data["error"] = str(e)

        return health_data

    # =========================================================================
    # Cache Setup and Management
    # =========================================================================

    async def _ensure_cache_directory(self) -> None:
        """Ensure cache directory exists with proper permissions."""
        try:
            if not self.cache_dir.exists():
                TreeLogger.info(
                    f"Creating cache directory: {self.cache_dir}", service="system"
                )
                self.cache_dir.mkdir(parents=True, exist_ok=True)

                TreeLogger.success(
                    "Cache directory created", {"path": str(self.cache_dir)}
                )

            # Verify write permissions
            test_file = self.cache_dir / ".write_test"
            test_file.touch()
            test_file.unlink()

            TreeLogger.info("Cache directory permissions verified", service="system")

        except Exception as e:
            raise ServiceError(
                f"Failed to create cache directory: {e}", service_name="MetadataCache"
            )

    async def _load_cache_from_disk(self) -> None:
        """Load existing cache from disk if available."""
        if not self.cache_file.exists():
            TreeLogger.info("No existing cache file found", service="system")
            return

        try:
            load_start_time = time.time()

            TreeLogger.info(f"Loading cache from {self.cache_file}", service="system")

            with open(self.cache_file, "r") as f:
                cache_data = json.load(f)

            # Load audio metadata cache
            if "audio_metadata" in cache_data:
                for key, data in cache_data["audio_metadata"].items():
                    self.audio_metadata_cache[key] = AudioFileInfo(**data)

            # Load reciter cache
            if "reciters" in cache_data:
                for key, data in cache_data["reciters"].items():
                    self.reciter_cache[key] = ReciterInfo(**data)

            # Load file hashes
            if "file_hashes" in cache_data:
                self.file_hash_cache.update(cache_data["file_hashes"])

            # Load statistics
            if "statistics" in cache_data:
                self.cache_stats.update(cache_data["statistics"])

            load_time = time.time() - load_start_time

            TreeLogger.success(
                "Cache loaded from disk",
                {
                    "load_time_ms": f"{load_time * 1000:.1f}",
                    "audio_entries": len(self.audio_metadata_cache),
                    "reciter_entries": len(self.reciter_cache),
                    "file_hashes": len(self.file_hash_cache),
                },
            )

        except Exception as e:
            TreeLogger.error(
                f"Failed to load cache from disk: {e}", None, service="system"
            )
            # Continue without cached data

    async def _save_cache_to_disk(self) -> None:
        """Save current cache to disk."""
        try:
            save_start_time = time.time()

            cache_data = {
                "audio_metadata": {
                    key: info.model_dump()
                    for key, info in self.audio_metadata_cache.items()
                },
                "reciters": {
                    key: info.model_dump() for key, info in self.reciter_cache.items()
                },
                "file_hashes": self.file_hash_cache,
                "statistics": self.cache_stats,
                "timestamp": datetime.now(APP_TIMEZONE).isoformat(),
            }

            with open(self.cache_file, "w") as f:
                json.dump(cache_data, f, indent=2, default=str)

            save_time = time.time() - save_start_time

            TreeLogger.info(
                "Cache saved to disk",
                {
                    "save_time_ms": f"{save_time * 1000:.1f}",
                    "file_size_kb": f"{self.cache_file.stat().st_size / 1024:.1f}",
                },
            )

        except Exception as e:
            TreeLogger.error("Failed to save cache to disk", None, {"error": str(e)})

    async def _initialize_surah_metadata(self) -> None:
        """Initialize Surah metadata cache."""
        TreeLogger.info("Initializing Surah metadata", service="system")

        try:
            # This would typically load from a JSON file or database
            # For now, we'll create basic entries for all 114 surahs
            surah_names = [
                "Al-Fatiha",
                "Al-Baqarah",
                "Ali 'Imran",
                "An-Nisa",
                "Al-Ma'idah",
                # ... (would include all 114 surah names)
            ]

            for i in range(1, 115):  # Surahs 1-114
                surah_name = (
                    surah_names[i - 1] if i - 1 < len(surah_names) else f"Surah {i}"
                )

                self.surah_cache[i] = SurahInfo(
                    number=i,
                    name_arabic=f"سورة {surah_name}",  # Simplified
                    name_english=surah_name,
                    meaning=f"Meaning of {surah_name}",
                    verses_count=1,  # Would be actual verse count
                    revelation_type="Meccan" if i <= 86 else "Medinan",  # Simplified
                    revelation_order=i,
                )

            TreeLogger.success(
                "Surah metadata initialized",
                {
                    "total_surahs": len(self.surah_cache),
                    "meccan_surahs": sum(
                        1 for s in self.surah_cache.values() if s.is_meccan
                    ),
                    "medinan_surahs": sum(
                        1 for s in self.surah_cache.values() if s.is_medinan
                    ),
                },
            )

        except Exception as e:
            TreeLogger.error(
                "Failed to initialize Surah metadata", None, {"error": str(e)}
            )

    async def _preload_audio_metadata(self) -> None:
        """Preload audio file metadata for fast access."""
        TreeLogger.info("Preloading audio metadata", service="system")

        preload_start_time = time.time()

        try:
            audio_folder = self.config.audio_folder
            if not audio_folder.exists():
                TreeLogger.warning(
                    f"Audio folder not found: {audio_folder}", service="system"
                )
                return

            preloaded_count = 0

            for reciter_folder in audio_folder.iterdir():
                if not reciter_folder.is_dir():
                    continue

                reciter_name = reciter_folder.name
                self.watched_directories.add(reciter_folder)

                TreeLogger.debug(
                    f"Preloading metadata for {reciter_name}", service="system"
                )

                # Scan audio files
                audio_files = []
                for audio_file in reciter_folder.glob("*.mp3"):
                    try:
                        # Generate cache key
                        cache_key = f"{reciter_name}:{audio_file.name}"

                        # Check if file has changed
                        file_mtime = audio_file.stat().st_mtime
                        if cache_key in self.audio_metadata_cache:
                            cached_info = self.audio_metadata_cache[cache_key]
                            if cached_info.last_accessed.timestamp() >= file_mtime:
                                continue  # Use cached version

                        # Extract surah number from filename
                        surah_number = int(audio_file.stem)

                        # Use cached duration if available, otherwise set to 0 (will be extracted lazily)
                        duration = 0.0
                        if cache_key in self.audio_metadata_cache:
                            duration = self.audio_metadata_cache[
                                cache_key
                            ].duration_seconds

                        # Create metadata
                        file_info = AudioFileInfo(
                            file_path=str(audio_file),
                            file_size=audio_file.stat().st_size,
                            duration_seconds=duration,
                            reciter=reciter_name,
                            surah_number=surah_number,
                            created_at=datetime.fromtimestamp(
                                audio_file.stat().st_ctime, APP_TIMEZONE
                            ),
                            last_accessed=datetime.now(APP_TIMEZONE),
                        )

                        self.audio_metadata_cache[cache_key] = file_info
                        audio_files.append(file_info)
                        preloaded_count += 1

                        # Store file modification time
                        self.file_modification_times[str(audio_file)] = file_mtime

                    except (ValueError, OSError) as e:
                        TreeLogger.warning(
                            f"Skipping invalid audio file {audio_file}: {e}",
                            service="system",
                        )
                        continue

                # Create reciter info
                if audio_files:
                    available_surahs = [f.surah_number for f in audio_files]
                    reciter_info = ReciterInfo(
                        name=reciter_name,
                        arabic_name=reciter_name,  # Would be proper Arabic name
                        directory=reciter_name,
                        total_surahs=len(audio_files),
                        available_surahs=available_surahs,
                        audio_quality=AudioQuality.HIGH,
                    )

                    self.reciter_cache[reciter_name] = reciter_info

            preload_time = time.time() - preload_start_time
            self.cache_stats["preloads"] += preloaded_count
            self.last_scan_time = datetime.now(APP_TIMEZONE)

            TreeLogger.success(
                "Audio metadata preloading complete",
                {
                    "preload_time_ms": f"{preload_time * 1000:.1f}",
                    "files_preloaded": preloaded_count,
                    "reciters_found": len(self.reciter_cache),
                    "directories_watched": len(self.watched_directories),
                },
            )

        except Exception as e:
            TreeLogger.error(
                "Audio metadata preloading failed", None, {"error": str(e)}
            )

    # =========================================================================
    # Cache Operations
    # =========================================================================

    async def get_audio_metadata(
        self, reciter: str, surah_number: int
    ) -> Optional[AudioFileInfo]:
        """Get audio file metadata with performance tracking."""
        lookup_start_time = time.time()
        self.cache_stats["total_requests"] += 1

        try:
            cache_key = f"{reciter}:{surah_number:03d}.mp3"

            TreeLogger.debug(
                f"Cache lookup for audio metadata",
                {
                    "cache_key": cache_key,
                    "reciter": reciter,
                    "surah": surah_number,
                    "cache_size": len(self.audio_metadata_cache),
                },
                service="MetadataCache",
            )

            # Check cache
            if cache_key in self.audio_metadata_cache:
                self.cache_stats["hits"] += 1
                TreeLogger.debug(f"Cache hit for {cache_key}", service="MetadataCache")

                # Update LRU cache
                self._update_lru_cache(cache_key)

                # Update access time
                metadata = self.audio_metadata_cache[cache_key]
                updated_metadata = metadata.update_access_time()
                self.audio_metadata_cache[cache_key] = updated_metadata

                lookup_time = time.time() - lookup_start_time
                self._track_lookup_time(lookup_time)

                TreeLogger.debug(f"Cache hit: {cache_key}", service="system")
                return updated_metadata

            # Cache miss - try to load from file system
            self.cache_stats["misses"] += 1
            TreeLogger.debug(f"Cache miss: {cache_key}", service="system")

            # Try to find and cache the file
            audio_file = self.config.audio_folder / reciter / f"{surah_number:03d}.mp3"
            if audio_file.exists():
                metadata = await self._create_audio_metadata(
                    audio_file, reciter, surah_number
                )
                self.audio_metadata_cache[cache_key] = metadata
                self._update_lru_cache(cache_key)

                lookup_time = time.time() - lookup_start_time
                self._track_lookup_time(lookup_time)

                return metadata

            lookup_time = time.time() - lookup_start_time
            self._track_lookup_time(lookup_time)

            return None

        except Exception as e:
            TreeLogger.error(
                f"Failed to get audio metadata for {reciter}:{surah_number}",
                None,
                {"error": str(e)},
            )
            return None

    async def get_reciter_info(self, reciter: str) -> Optional[ReciterInfo]:
        """Get reciter information from cache."""
        self.cache_stats["total_requests"] += 1

        if reciter in self.reciter_cache:
            self.cache_stats["hits"] += 1
            TreeLogger.debug(f"Reciter cache hit: {reciter}", service="system")
            return self.reciter_cache[reciter]

        self.cache_stats["misses"] += 1
        TreeLogger.debug(f"Reciter cache miss: {reciter}", service="system")
        return None

    async def get_surah_info(self, surah_number: int) -> Optional[SurahInfo]:
        """Get Surah information from cache."""
        self.cache_stats["total_requests"] += 1

        if surah_number in self.surah_cache:
            self.cache_stats["hits"] += 1
            TreeLogger.debug(f"Surah cache hit: {surah_number}", service="system")
            return self.surah_cache[surah_number]

        self.cache_stats["misses"] += 1
        TreeLogger.debug(f"Surah cache miss: {surah_number}", service="system")
        return None

    async def _extract_audio_duration(self, file_path: str) -> Optional[float]:
        """Extract audio duration using mutagen."""
        try:
            # Use mutagen - synchronous but very fast
            audio = MP3(file_path)
            if audio.info and hasattr(audio.info, "length"):
                duration = audio.info.length
                TreeLogger.debug(
                    f"Extracted duration: {duration}s for {file_path}",
                    service="MetadataCache",
                )
                return duration

        except Exception as e:
            TreeLogger.error(
                f"Error extracting duration from {file_path}: {e}",
                service="MetadataCache",
            )

        return None

    async def _create_audio_metadata(
        self, audio_file: Path, reciter: str, surah_number: int
    ) -> AudioFileInfo:
        """Create audio metadata for a file."""
        try:
            # Extract duration using ffprobe
            duration = await self._extract_audio_duration(str(audio_file))

            return AudioFileInfo(
                file_path=str(audio_file),
                file_size=audio_file.stat().st_size,
                duration_seconds=duration if duration is not None else 0.0,
                reciter=reciter,
                surah_number=surah_number,
                created_at=datetime.fromtimestamp(
                    audio_file.stat().st_ctime, APP_TIMEZONE
                ),
                last_accessed=datetime.now(APP_TIMEZONE),
            )
        except Exception as e:
            TreeLogger.error(
                f"Failed to create metadata for {audio_file}", None, {"error": str(e)}
            )
            raise

    # =========================================================================
    # Cache Management
    # =========================================================================

    def _update_lru_cache(self, key: str) -> None:
        """Update LRU cache for frequently accessed items."""
        # Move to end (most recently used)
        if key in self.lru_cache:
            self.lru_cache.move_to_end(key)
        else:
            self.lru_cache[key] = True

            # Evict oldest if over limit
            if len(self.lru_cache) > self.max_lru_size:
                oldest_key = next(iter(self.lru_cache))
                del self.lru_cache[oldest_key]
                self.cache_stats["evictions"] += 1

    def _track_lookup_time(self, lookup_time: float) -> None:
        """Track lookup time for performance monitoring."""
        self.lookup_times.append(lookup_time)

        # Keep only recent lookup times
        if len(self.lookup_times) > self.max_lookup_history:
            self.lookup_times = self.lookup_times[-self.max_lookup_history :]

        # Update average
        if self.lookup_times:
            self.cache_stats["average_lookup_time"] = sum(self.lookup_times) / len(
                self.lookup_times
            )

    async def _calculate_memory_usage(self) -> None:
        """Calculate approximate memory usage of cache."""
        try:
            # Rough estimation of memory usage
            audio_size = len(self.audio_metadata_cache) * 1024  # ~1KB per entry
            reciter_size = len(self.reciter_cache) * 512  # ~512B per entry
            surah_size = len(self.surah_cache) * 256  # ~256B per entry
            lru_size = len(self.lru_cache) * 64  # ~64B per entry

            total_bytes = audio_size + reciter_size + surah_size + lru_size
            self.cache_stats["cache_size_mb"] = total_bytes / 1024 / 1024

        except Exception as e:
            TreeLogger.error(
                "Failed to calculate memory usage", None, {"error": str(e)}
            )

    def _calculate_hit_rate(self) -> float:
        """Calculate cache hit rate percentage."""
        total_requests = self.cache_stats["hits"] + self.cache_stats["misses"]
        if total_requests == 0:
            return 100.0
        return (self.cache_stats["hits"] / total_requests) * 100.0

    # =========================================================================
    # Background Tasks
    # =========================================================================

    async def _start_cleanup_task(self) -> None:
        """Start automatic cache cleanup task."""

        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(self.auto_cleanup_interval)
                    await self._perform_cache_cleanup()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    TreeLogger.error(
                        "Cache cleanup task error", None, {"error": str(e)}
                    )

        self.cleanup_task = asyncio.create_task(cleanup_loop())
        TreeLogger.info(
            f"Cache cleanup task started (interval: {self.auto_cleanup_interval}s)",
            service="system",
        )

    async def _start_file_watcher_task(self) -> None:
        """Start file system monitoring task."""

        async def file_watcher_loop():
            while True:
                try:
                    await asyncio.sleep(60.0)  # Check every minute
                    await self._check_file_changes()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    TreeLogger.error("File watcher task error", None, {"error": str(e)})

        self.file_watcher_task = asyncio.create_task(file_watcher_loop())
        TreeLogger.info("File watcher task started", service="system")

    async def _stop_background_tasks(self) -> None:
        """Stop all background tasks."""
        tasks_to_stop = []

        if self.cleanup_task and not self.cleanup_task.done():
            tasks_to_stop.append(("cleanup", self.cleanup_task))

        if self.file_watcher_task and not self.file_watcher_task.done():
            tasks_to_stop.append(("file_watcher", self.file_watcher_task))

        for task_name, task in tasks_to_stop:
            try:
                task.cancel()
                await task
                TreeLogger.info(f"{task_name} task stopped", service="system")
            except asyncio.CancelledError:
                pass
            except Exception as e:
                TreeLogger.error(
                    f"Error stopping {task_name} task", None, {"error": str(e)}
                )

    async def _perform_cache_cleanup(self) -> None:
        """Perform cache cleanup and memory management."""
        try:
            cleanup_start_time = time.time()

            # Calculate current memory usage
            await self._calculate_memory_usage()

            # Check if cleanup is needed
            if self.cache_stats["cache_size_mb"] > self.memory_limit_mb:
                TreeLogger.info(
                    "Cache memory limit exceeded, performing cleanup", service="system"
                )

                # Remove least recently used items
                items_to_remove = len(self.lru_cache) // 4  # Remove 25%
                for _ in range(items_to_remove):
                    if self.lru_cache:
                        oldest_key = next(iter(self.lru_cache))
                        del self.lru_cache[oldest_key]

                        # Remove from main cache if exists
                        if oldest_key in self.audio_metadata_cache:
                            del self.audio_metadata_cache[oldest_key]

                        self.cache_stats["evictions"] += 1

                self.cache_stats["memory_cleanups"] += 1

            # Update statistics
            self.cache_stats["hit_rate"] = self._calculate_hit_rate()

            cleanup_time = time.time() - cleanup_start_time

            TreeLogger.debug(
                "Cache cleanup completed",
                {
                    "cleanup_time_ms": f"{cleanup_time * 1000:.1f}",
                    "memory_usage_mb": f"{self.cache_stats['cache_size_mb']:.2f}",
                    "hit_rate": f"{self.cache_stats['hit_rate']:.1f}%",
                },
                service="system",
            )

        except Exception as e:
            TreeLogger.error("Cache cleanup failed", None, {"error": str(e)})

    async def _check_file_changes(self) -> None:
        """Check for file system changes and update cache."""
        try:
            changes_detected = 0

            for directory in self.watched_directories:
                if not directory.exists():
                    continue

                for audio_file in directory.glob("*.mp3"):
                    file_path = str(audio_file)
                    current_mtime = audio_file.stat().st_mtime

                    if file_path in self.file_modification_times:
                        if current_mtime > self.file_modification_times[file_path]:
                            # File has been modified
                            TreeLogger.info(
                                f"File change detected: {audio_file.name}",
                                service="system",
                            )

                            # Invalidate cache entry
                            cache_key = f"{directory.name}:{audio_file.name}"
                            if cache_key in self.audio_metadata_cache:
                                del self.audio_metadata_cache[cache_key]

                            self.file_modification_times[file_path] = current_mtime
                            changes_detected += 1
                    else:
                        # New file
                        self.file_modification_times[file_path] = current_mtime
                        changes_detected += 1

            if changes_detected > 0:
                TreeLogger.info(
                    f"Detected {changes_detected} file changes", service="system"
                )

        except Exception as e:
            TreeLogger.error("File change detection failed", None, {"error": str(e)})

    # =========================================================================
    # File System Monitoring
    # =========================================================================

    async def _setup_file_watching(self) -> None:
        """Setup file system monitoring for audio directories."""
        try:
            audio_folder = self.config.audio_folder
            if not audio_folder.exists():
                TreeLogger.warning(
                    "Audio folder not found for file watching", service="system"
                )
                return

            # Add all reciter directories to watch list
            for reciter_folder in audio_folder.iterdir():
                if reciter_folder.is_dir():
                    self.watched_directories.add(reciter_folder)

            TreeLogger.info(
                f"File watching setup complete",
                {"watched_directories": len(self.watched_directories)},
            )

        except Exception as e:
            TreeLogger.error("File watching setup failed", None, {"error": str(e)})

    # =========================================================================
    # Statistics and Logging
    # =========================================================================

    async def _log_startup_statistics(self) -> None:
        """Log cache statistics at startup."""
        TreeLogger.info(
            "Metadata cache startup statistics",
            context={
                "audio_metadata_entries": len(self.audio_metadata_cache),
                "reciter_entries": len(self.reciter_cache),
                "surah_entries": len(self.surah_cache),
                "memory_usage_mb": f"{self.cache_stats['cache_size_mb']:.2f}",
                "preloaded_files": self.cache_stats["preloads"],
                "watched_directories": len(self.watched_directories),
            },
        )

    async def _log_final_statistics(self) -> None:
        """Log final cache statistics at shutdown."""
        TreeLogger.info(
            "Metadata cache final statistics",
            context={
                "total_requests": self.cache_stats["total_requests"],
                "cache_hits": self.cache_stats["hits"],
                "cache_misses": self.cache_stats["misses"],
                "hit_rate": f"{self._calculate_hit_rate():.1f}%",
                "evictions": self.cache_stats["evictions"],
                "memory_cleanups": self.cache_stats["memory_cleanups"],
                "average_lookup_ms": f"{self.cache_stats['average_lookup_time'] * 1000:.2f}",
                "final_memory_mb": f"{self.cache_stats['cache_size_mb']:.2f}",
            },
        )

    # =========================================================================
    # Public Interface
    # =========================================================================

    async def invalidate_cache(self, pattern: Optional[str] = None) -> int:
        """Invalidate cache entries matching pattern."""
        try:
            if pattern is None:
                # Clear all caches
                count = len(self.audio_metadata_cache) + len(self.reciter_cache)
                self.audio_metadata_cache.clear()
                self.reciter_cache.clear()
                self.lru_cache.clear()
            else:
                # Clear entries matching pattern
                count = 0
                keys_to_remove = [
                    key for key in self.audio_metadata_cache.keys() if pattern in key
                ]
                for key in keys_to_remove:
                    del self.audio_metadata_cache[key]
                    if key in self.lru_cache:
                        del self.lru_cache[key]
                    count += 1

            TreeLogger.info(
                f"Cache invalidated: {count} entries removed", service="system"
            )
            return count

        except Exception as e:
            TreeLogger.error("Cache invalidation failed", None, {"error": str(e)})
            return 0

    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        return {
            **self.cache_stats,
            "cache_sizes": {
                "audio_metadata": len(self.audio_metadata_cache),
                "reciters": len(self.reciter_cache),
                "surahs": len(self.surah_cache),
                "lru_cache": len(self.lru_cache),
            },
            "hit_rate": self._calculate_hit_rate(),
            "memory_usage_mb": self.cache_stats["cache_size_mb"],
            "watched_directories": len(self.watched_directories),
            "last_scan": (
                self.last_scan_time.isoformat() if self.last_scan_time else None
            ),
        }
