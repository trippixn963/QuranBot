# =============================================================================
# QuranBot - Metadata Cache Service
# =============================================================================
# This module provides a high-performance caching layer for audio file metadata
# with LRU eviction, async operations, and automatic cache warming.
# =============================================================================

import asyncio
from collections import OrderedDict
from datetime import UTC, datetime
import hashlib
from pathlib import Path

from mutagen.mp3 import MP3

from src.core.exceptions import AudioError
from src.core.logger import StructuredLogger
from src.data.models import AudioCache, AudioFileInfo, ReciterInfo


class MetadataCache:
    """
    High-performance metadata cache with LRU eviction and async operations.

    This cache service provides fast access to audio file metadata including
    duration, file size, and other properties. It uses an LRU eviction policy
    and supports background cache warming for optimal performance.
    """

    def __init__(
        self,
        logger: StructuredLogger,
        max_size: int = 1000,
        enable_persistence: bool = True,
        cache_file: Path | None = None,
    ):
        """
        Initialize the metadata cache.

        Args:
            logger: Structured logger for cache operations
            max_size: Maximum number of cache entries (LRU eviction)
            enable_persistence: Whether to persist cache to disk
            cache_file: Path to cache persistence file
        """
        self._logger = logger
        self._max_size = max_size
        self._enable_persistence = enable_persistence
        self._cache_file = cache_file or Path("data/metadata_cache.json")

        # Health monitor (will be set if available)
        self._health_monitor = None

        # LRU cache implementation using OrderedDict
        self._cache: OrderedDict[str, AudioCache] = OrderedDict()
        self._access_lock = asyncio.Lock()

        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0

        # Background tasks
        self._cleanup_task: asyncio.Task | None = None
        self._persistence_task: asyncio.Task | None = None

    async def initialize(self) -> None:
        """Initialize the cache and start background tasks"""
        await self._load_from_disk()

        # Start background cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        # Start persistence task if enabled
        if self._enable_persistence:
            self._persistence_task = asyncio.create_task(self._persistence_loop())

        await self._logger.info(
            "Metadata cache initialized",
            {
                "max_size": self._max_size,
                "persistence_enabled": self._enable_persistence,
                "cached_items": len(self._cache),
            },
        )

    def set_health_monitor(self, health_monitor):
        """Set health monitor for reporting JSON operations"""
        self._health_monitor = health_monitor

    async def shutdown(self) -> None:
        """Shutdown the cache and save to disk"""
        # Cancel background tasks
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        if self._persistence_task:
            self._persistence_task.cancel()
            try:
                await self._persistence_task
            except asyncio.CancelledError:
                pass

        # Save final state to disk
        if self._enable_persistence:
            await self._save_to_disk()

        await self._logger.info(
            "Metadata cache shutdown complete",
            {
                "final_size": len(self._cache),
                "total_hits": self._hits,
                "total_misses": self._misses,
                "total_evictions": self._evictions,
            },
        )

    # Logger will be set in real implementation
    async def get_file_info(
        self, file_path: Path, reciter: str, surah_number: int
    ) -> AudioFileInfo | None:
        """
        Get audio file information from cache or filesystem.

        Args:
            file_path: Path to the audio file
            reciter: Name of the reciter
            surah_number: Surah number (1-114)

        Returns:
            AudioFileInfo object or None if file doesn't exist
        """
        cache_key = self._generate_cache_key(file_path, reciter, surah_number)

        async with self._access_lock:
            # Check cache first
            if cache_key in self._cache:
                cache_entry = self._cache[cache_key]

                # Move to end (most recently used)
                self._cache.move_to_end(cache_key)
                cache_entry.access_count += 1
                cache_entry.last_accessed = datetime.now(UTC)

                self._hits += 1

                # Verify file still exists and hasn't changed
                if await self._is_cache_entry_valid(cache_entry, file_path):
                    return self._cache_to_file_info(cache_entry)
                else:
                    # File has changed, remove from cache
                    del self._cache[cache_key]

        # Cache miss - load from filesystem
        self._misses += 1
        file_info = await self._load_file_metadata(file_path, reciter, surah_number)

        if file_info:
            await self._cache_file_info(file_info, cache_key)

        return file_info

    async def warm_cache_for_reciter(
        self, reciter_info: ReciterInfo, audio_base_folder: Path
    ) -> None:
        """
        Pre-populate cache with metadata for all files of a reciter.

        Args:
            reciter_info: Information about the reciter
            audio_base_folder: Base audio folder path
        """
        reciter_folder = audio_base_folder / reciter_info.folder_name
        if not reciter_folder.exists():
            return

        await self._logger.info(
            "Starting cache warming for reciter",
            {
                "reciter": reciter_info.name,
                "folder": str(reciter_folder),
                "expected_files": reciter_info.file_count,
            },
        )

        # Find all MP3 files
        mp3_files = list(reciter_folder.glob("*.mp3"))
        loaded_count = 0

        for file_path in mp3_files:
            try:
                # Extract surah number from filename
                surah_number = self._extract_surah_number(file_path.name)
                if surah_number:
                    await self.get_file_info(file_path, reciter_info.name, surah_number)
                    loaded_count += 1
            except Exception as e:
                await self._logger.warning(
                    "Failed to load metadata during cache warming",
                    {
                        "file": str(file_path),
                        "reciter": reciter_info.name,
                        "error": str(e),
                    },
                )

        await self._logger.info(
            "Cache warming completed for reciter",
            {
                "reciter": reciter_info.name,
                "files_loaded": loaded_count,
                "total_files": len(mp3_files),
                "cache_size": len(self._cache),
            },
        )

    async def get_cache_stats(self) -> dict[str, any]:
        """Get cache performance statistics"""
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "cache_size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate_percent": round(hit_rate, 2),
            "evictions": self._evictions,
            "memory_usage_percent": round((len(self._cache) / self._max_size) * 100, 2),
        }

    async def clear_cache(self) -> None:
        """Clear all cache entries"""
        async with self._access_lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
            self._evictions = 0

        await self._logger.info("Cache cleared")

    async def invalidate_reciter(self, reciter: str) -> int:
        """
        Invalidate all cache entries for a specific reciter.

        Args:
            reciter: Name of the reciter to invalidate

        Returns:
            Number of entries removed
        """
        removed_count = 0

        async with self._access_lock:
            keys_to_remove = [
                key for key, entry in self._cache.items() if entry.reciter == reciter
            ]

            for key in keys_to_remove:
                del self._cache[key]
                removed_count += 1

        await self._logger.info(
            "Invalidated cache entries for reciter",
            {"reciter": reciter, "entries_removed": removed_count},
        )

        return removed_count

    def _generate_cache_key(
        self, file_path: Path, reciter: str, surah_number: int
    ) -> str:
        """Generate a unique cache key for a file"""
        return f"{reciter}:{surah_number}:{file_path.name}"

    async def _load_file_metadata(
        self, file_path: Path, reciter: str, surah_number: int
    ) -> AudioFileInfo | None:
        """Load metadata from an audio file"""
        try:
            if not file_path.exists():
                return None

            # Get file stats
            stat = file_path.stat()
            file_size = stat.st_size
            created_at = datetime.fromtimestamp(stat.st_ctime, tz=UTC)
            last_modified = datetime.fromtimestamp(stat.st_mtime, tz=UTC)

            # Load audio metadata using mutagen
            duration_seconds = None
            bitrate = None

            try:
                audio = MP3(str(file_path))
                if audio.info:
                    duration_seconds = audio.info.length
                    bitrate = (
                        f"{audio.info.bitrate}kbps" if audio.info.bitrate else None
                    )
            except Exception as e:
                await self._logger.warning(
                    "Failed to load audio metadata",
                    {"file": str(file_path), "error": str(e)},
                )

            return AudioFileInfo(
                file_path=file_path,
                surah_number=surah_number,
                reciter=reciter,
                duration_seconds=duration_seconds,
                file_size_bytes=file_size,
                bitrate=bitrate,
                format="mp3",
                created_at=created_at,
                last_modified=last_modified,
            )

        except Exception as e:
            raise AudioError(
                f"Failed to load metadata for {file_path}",
                context={
                    "file_path": str(file_path),
                    "reciter": reciter,
                    "surah_number": surah_number,
                    "operation": "metadata_loading",
                },
                original_error=e,
            )

    async def _cache_file_info(self, file_info: AudioFileInfo, cache_key: str) -> None:
        """Add file info to cache"""
        async with self._access_lock:
            # Create cache entry
            cache_entry = AudioCache(
                reciter=file_info.reciter,
                surah_number=file_info.surah_number,
                file_path=str(file_info.file_path),
                duration=file_info.duration_seconds,
                file_size=file_info.file_size_bytes,
                file_hash=self._calculate_file_hash(file_info.file_path),
                last_accessed=datetime.now(UTC),
                access_count=1,
            )

            # Add to cache
            self._cache[cache_key] = cache_entry

            # Check if we need to evict old entries
            if len(self._cache) > self._max_size:
                # Remove least recently used entry
                oldest_key, _ = self._cache.popitem(last=False)
                self._evictions += 1

                await self._logger.debug(
                    "Evicted cache entry",
                    {"evicted_key": oldest_key, "cache_size": len(self._cache)},
                )

    def _cache_to_file_info(self, cache_entry: AudioCache) -> AudioFileInfo:
        """Convert cache entry to AudioFileInfo"""
        file_path = Path(cache_entry.file_path)

        return AudioFileInfo(
            file_path=file_path,
            surah_number=cache_entry.surah_number,
            reciter=cache_entry.reciter,
            duration_seconds=cache_entry.duration,
            file_size_bytes=cache_entry.file_size,
            bitrate=None,  # Not stored in cache
            format="mp3",
            created_at=None,  # Not stored in cache
            last_modified=None,  # Not stored in cache
        )

    async def _is_cache_entry_valid(
        self, cache_entry: AudioCache, file_path: Path
    ) -> bool:
        """Check if cache entry is still valid"""
        try:
            if not file_path.exists():
                return False

            # Check if file has changed
            current_hash = self._calculate_file_hash(file_path)
            return current_hash == cache_entry.file_hash

        except Exception:
            return False

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate a quick hash of the file for change detection"""
        try:
            stat = file_path.stat()
            # Use file size and modification time for quick hash
            hash_input = f"{stat.st_size}:{stat.st_mtime}"
            return hashlib.md5(hash_input.encode()).hexdigest()[:16]
        except Exception:
            return ""

    def _extract_surah_number(self, filename: str) -> int | None:
        """Extract surah number from filename"""
        import re

        match = re.search(r"(\d+)", filename)
        if match:
            surah_num = int(match.group(1))
            return surah_num if 1 <= surah_num <= 114 else None
        return None

    async def _cleanup_loop(self) -> None:
        """Background task to clean up expired cache entries"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour

                async with self._access_lock:
                    # Find entries that haven't been accessed in a while
                    cutoff_time = datetime.now(UTC).timestamp() - 3600  # 1 hour
                    keys_to_remove = []

                    for key, entry in self._cache.items():
                        if (
                            entry.last_accessed.timestamp() < cutoff_time
                            and entry.access_count < 2
                        ):
                            keys_to_remove.append(key)

                    # Remove old entries
                    for key in keys_to_remove:
                        del self._cache[key]

                    if keys_to_remove:
                        await self._logger.debug(
                            "Cleaned up unused cache entries",
                            {
                                "removed_count": len(keys_to_remove),
                                "cache_size": len(self._cache),
                            },
                        )

            except asyncio.CancelledError:
                break
            except Exception as e:
                await self._logger.error(
                    "Error in cache cleanup loop", {"error": str(e)}
                )

    async def _persistence_loop(self) -> None:
        """Background task to persist cache to disk"""
        while True:
            try:
                await asyncio.sleep(3600)  # Save every hour
                await self._save_to_disk()

            except asyncio.CancelledError:
                break
            except Exception as e:
                await self._logger.error(
                    "Error in cache persistence loop", {"error": str(e)}
                )

    async def _save_to_disk(self) -> None:
        """Save cache to disk"""
        try:
            if not self._cache_file.parent.exists():
                self._cache_file.parent.mkdir(parents=True, exist_ok=True)

            # Convert cache to serializable format
            cache_data = {
                "version": "1.0",
                "timestamp": datetime.now(UTC).isoformat(),
                "entries": {},
            }

            async with self._access_lock:
                for key, entry in self._cache.items():
                    # Convert to dict and handle datetime serialization
                    entry_dict = entry.dict()

                    # Convert datetime objects to ISO format strings
                    datetime_fields = ["created_at", "last_modified", "last_accessed"]
                    for field in datetime_fields:
                        if entry_dict.get(field):
                            entry_dict[field] = entry_dict[field].isoformat()

                    # Convert Path objects to strings
                    if "file_path" in entry_dict:
                        entry_dict["file_path"] = str(entry_dict["file_path"])

                    cache_data["entries"][key] = entry_dict

            # Write to disk
            import json

            import aiofiles

            async with aiofiles.open(self._cache_file, "w") as f:
                await f.write(json.dumps(cache_data, indent=2))

            await self._logger.debug(
                "Cache saved to disk",
                {"entries": len(cache_data["entries"]), "file": str(self._cache_file)},
            )

            # Report successful save to health monitor
            if self._health_monitor:
                await self._health_monitor.report_json_save(self._cache_file.name, True)

        except Exception as e:
            await self._logger.error(
                "Failed to save cache to disk",
                {"error": str(e), "file": str(self._cache_file)},
            )

            # Report failed save to health monitor
            if self._health_monitor:
                await self._health_monitor.report_json_save(
                    self._cache_file.name, False, str(e)
                )

    async def _load_from_disk(self) -> None:
        """Load cache from disk"""
        try:
            if not self._cache_file.exists():
                return

            import json

            import aiofiles

            async with aiofiles.open(self._cache_file) as f:
                cache_data = json.loads(await f.read())

            # Load cache entries
            loaded_count = 0
            for key, entry_data in cache_data.get("entries", {}).items():
                try:
                    # Handle datetime deserialization
                    if entry_data.get("last_accessed"):
                        try:
                            from datetime import datetime

                            entry_data["last_accessed"] = datetime.fromisoformat(
                                entry_data["last_accessed"]
                            )
                        except (ValueError, TypeError):
                            # If datetime parsing fails, use current time
                            entry_data["last_accessed"] = datetime.now(UTC)

                    # Handle other datetime fields if they exist
                    for datetime_field in ["created_at", "last_modified"]:
                        if entry_data.get(datetime_field):
                            try:
                                entry_data[datetime_field] = datetime.fromisoformat(
                                    entry_data[datetime_field]
                                )
                            except (ValueError, TypeError):
                                entry_data[datetime_field] = None

                    cache_entry = AudioCache(**entry_data)
                    self._cache[key] = cache_entry
                    loaded_count += 1
                except Exception as e:
                    await self._logger.warning(
                        "Failed to load cache entry", {"key": key, "error": str(e)}
                    )

            await self._logger.info(
                "Cache loaded from disk",
                {"entries_loaded": loaded_count, "file": str(self._cache_file)},
            )

        except Exception as e:
            await self._logger.warning(
                "Failed to load cache from disk",
                {"error": str(e), "file": str(self._cache_file)},
            )
