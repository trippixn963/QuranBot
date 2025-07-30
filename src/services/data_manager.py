"""QuranBot - Hybrid Data Manager.

Manages both SQLite database and JSON files with smart synchronization.
Provides easy manual editing of JSON files while maintaining SQLite performance.

This module provides a unified data management system that:
- Keeps editable content in JSON files (quiz questions, verses, etc.)
- Uses SQLite for critical state data and performance
- Automatically syncs JSON changes to SQLite
- Provides atomic backup of both systems
- Maintains data integrity across both storage types

Classes:
    HybridDataManager: Unified data management with JSON/SQLite sync
    JSONContentManager: Manages editable JSON content files
    DataBackupManager: Atomic backup and restore system
"""

import asyncio
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from ..core.logger import StructuredLogger
from .state_service import SQLiteStateService


class JSONContentManager:
    """Manages editable JSON content files with change detection."""

    def __init__(self, logger: StructuredLogger, data_dir: Path = Path("data")):
        self.logger = logger
        self.data_dir = data_dir
        self.content_files = {
            "quiz_questions": "quiz.json",
            "daily_verses": "verses.json",
            "syrian_knowledge": "knowledge.json",
            "rich_presence": "presence.json",
            "quiz_state": "state.json",
            "prayer_cache": "prayer_cache.json",
        }
        self.file_hashes = {}  # Track file changes
        self._load_file_hashes()

    def _load_file_hashes(self):
        """Load current file hashes to detect changes."""
        for content_type, filename in self.content_files.items():
            file_path = self.data_dir / filename
            if file_path.exists():
                try:
                    with open(file_path, encoding="utf-8") as f:
                        content = f.read()
                        self.file_hashes[content_type] = hashlib.md5(
                            content.encode()
                        ).hexdigest()
                except Exception as e:
                    self.logger.warning(f"Failed to load hash for {filename}: {e}")

    def detect_changes(self) -> list[str]:
        """Detect which JSON files have changed since last check."""
        changed_files = []

        for content_type, filename in self.content_files.items():
            file_path = self.data_dir / filename
            if not file_path.exists():
                continue

            try:
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()
                    current_hash = hashlib.md5(content.encode()).hexdigest()

                    if (
                        content_type not in self.file_hashes
                        or self.file_hashes[content_type] != current_hash
                    ):
                        changed_files.append(content_type)
                        self.file_hashes[content_type] = current_hash

            except Exception as e:
                self.logger.error(f"Failed to check {filename} for changes: {e}")

        return changed_files

    def load_json_content(self, content_type: str) -> dict[str, Any] | None:
        """Load JSON content safely."""
        if content_type not in self.content_files:
            return None

        file_path = self.data_dir / self.content_files[content_type]
        if not file_path.exists():
            return None

        try:
            with open(file_path, encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON corruption detected in {file_path}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Failed to load {file_path}: {e}")
            return None

    def save_json_content(self, content_type: str, data: dict[str, Any]) -> bool:
        """Save JSON content safely with atomic write."""
        if content_type not in self.content_files:
            return False

        file_path = self.data_dir / self.content_files[content_type]
        temp_path = file_path.with_suffix(".tmp")

        try:
            # Write to temporary file first
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # Atomic move
            temp_path.replace(file_path)

            # Update hash
            self.file_hashes[content_type] = hashlib.md5(
                json.dumps(data, ensure_ascii=False).encode()
            ).hexdigest()

            return True
        except Exception as e:
            self.logger.error(f"Failed to save {file_path}: {e}")
            if temp_path.exists():
                temp_path.unlink()
            return False


class DataBackupManager:
    """Manages atomic backup and restore of all data."""

    def __init__(self, logger: StructuredLogger, data_dir: Path = Path("data")):
        self.logger = logger
        self.data_dir = data_dir
        self.backup_dir = data_dir / "backups"
        self.backup_dir.mkdir(exist_ok=True)

    async def create_backup(self, state_service: SQLiteStateService) -> Path | None:
        """Create atomic backup of all data (SQLite + JSON)."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"backup_{timestamp}"
        backup_path.mkdir(exist_ok=True)

        try:
            # 1. Backup SQLite database
            db_backup_path = backup_path / "quranbot.db"
            await state_service.backup_database(db_backup_path)

            # 2. Backup JSON files
            json_backup_path = backup_path / "json_files"
            json_backup_path.mkdir(exist_ok=True)

            for file_path in self.data_dir.glob("*.json"):
                if file_path.is_file():
                    import shutil

                    shutil.copy2(file_path, json_backup_path / file_path.name)

            # 3. Create backup manifest
            manifest = {
                "backup_timestamp": datetime.now().isoformat(),
                "sqlite_size": (
                    db_backup_path.stat().st_size if db_backup_path.exists() else 0
                ),
                "json_files": [f.name for f in json_backup_path.glob("*.json")],
                "total_files": len(list(json_backup_path.glob("*.json"))) + 1,
            }

            with open(backup_path / "manifest.json", "w") as f:
                json.dump(manifest, f, indent=2)

            await self.logger.info(
                "Backup created successfully",
                {
                    "backup_path": str(backup_path),
                    "sqlite_size": manifest["sqlite_size"],
                    "json_files": len(manifest["json_files"]),
                },
            )

            return backup_path

        except Exception as e:
            await self.logger.error("Backup failed", {"error": str(e)})
            # Cleanup failed backup
            if backup_path.exists():
                import shutil

                shutil.rmtree(backup_path)
            return None

    async def restore_backup(
        self, backup_path: Path, state_service: SQLiteStateService
    ) -> bool:
        """Restore from backup with verification."""
        try:
            # 1. Verify backup integrity
            manifest_path = backup_path / "manifest.json"
            if not manifest_path.exists():
                await self.logger.error("Backup manifest not found")
                return False

            with open(manifest_path) as f:
                manifest = json.load(f)

            # 2. Stop all services (would be called externally)
            await self.logger.info(
                "Starting backup restoration", {"backup_path": str(backup_path)}
            )

            # 3. Restore SQLite database
            db_backup_path = backup_path / "quranbot.db"
            if db_backup_path.exists():
                import shutil

                shutil.copy2(db_backup_path, self.data_dir / "quranbot.db")

            # 4. Restore JSON files
            json_backup_path = backup_path / "json_files"
            if json_backup_path.exists():
                for json_file in json_backup_path.glob("*.json"):
                    import shutil

                    shutil.copy2(json_file, self.data_dir / json_file.name)

            await self.logger.info("Backup restoration completed successfully")
            return True

        except Exception as e:
            await self.logger.error("Backup restoration failed", {"error": str(e)})
            return False


class HybridDataManager:
    """Unified data management with JSON/SQLite sync."""

    def __init__(self, logger: StructuredLogger, state_service: SQLiteStateService):
        self.logger = logger
        self.state_service = state_service
        self.json_manager = JSONContentManager(logger)
        self.backup_manager = DataBackupManager(logger)
        self.sync_interval = 300  # 5 minutes
        self._sync_task = None

    async def initialize(self) -> None:
        """Initialize the hybrid data manager."""
        await self.state_service.initialize()

        # Start sync task
        self._sync_task = asyncio.create_task(self._sync_loop())

        await self.logger.info("Hybrid data manager initialized")

    async def shutdown(self) -> None:
        """Shutdown the hybrid data manager."""
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass

        await self.state_service.shutdown()
        await self.logger.info("Hybrid data manager shutdown")

    async def _sync_loop(self) -> None:
        """Periodic sync loop to detect JSON changes."""
        while True:
            try:
                await asyncio.sleep(self.sync_interval)

                # Detect JSON changes
                changed_files = self.json_manager.detect_changes()

                if changed_files:
                    await self.logger.info(
                        "JSON changes detected", {"changed_files": changed_files}
                    )

                    # Sync changed files to SQLite
                    for content_type in changed_files:
                        await self._sync_json_to_sqlite(content_type)

            except asyncio.CancelledError:
                break
            except Exception as e:
                await self.logger.error("Sync loop error", {"error": str(e)})
                await asyncio.sleep(60)  # Wait before retrying

    async def _sync_json_to_sqlite(self, content_type: str) -> None:
        """Sync JSON content to SQLite for performance."""
        content = self.json_manager.load_json_content(content_type)
        if not content:
            return

        try:
            # Store in SQLite for fast access
            await self.state_service.set_metadata_cache(f"{content_type}_data", content)

            await self.logger.info(
                f"Synced {content_type} to SQLite",
                {"content_type": content_type, "data_size": len(str(content))},
            )

        except Exception as e:
            await self.logger.error(f"Failed to sync {content_type}", {"error": str(e)})

    async def get_content(
        self, content_type: str, use_cache: bool = True
    ) -> dict[str, Any] | None:
        """Get content with smart caching strategy."""
        # Try SQLite cache first for performance
        if use_cache:
            cached_data = await self.state_service.get_metadata_cache(
                f"{content_type}_data"
            )
            if cached_data:
                return cached_data

        # Fall back to JSON file
        return self.json_manager.load_json_content(content_type)

    async def update_content(self, content_type: str, data: dict[str, Any]) -> bool:
        """Update content in both JSON and SQLite."""
        # Update JSON file
        if not self.json_manager.save_json_content(content_type, data):
            return False

        # Sync to SQLite
        await self._sync_json_to_sqlite(content_type)

        await self.logger.info(
            f"Updated {content_type}", {"content_type": content_type}
        )
        return True

    async def create_backup(self) -> Path | None:
        """Create atomic backup of all data."""
        return await self.backup_manager.create_backup(self.state_service)

    async def restore_backup(self, backup_path: Path) -> bool:
        """Restore from backup."""
        return await self.backup_manager.restore_backup(backup_path, self.state_service)

    async def verify_data_integrity(self) -> dict[str, Any]:
        """Verify integrity of all data."""
        integrity_report = {
            "sqlite_integrity": False,
            "json_files": {},
            "overall_status": "unknown",
        }

        try:
            # Check SQLite integrity
            db_stats = await self.state_service.get_database_stats()
            integrity_report["sqlite_integrity"] = db_stats.get("status") == "healthy"

            # Check JSON files
            for content_type, filename in self.json_manager.content_files.items():
                file_path = self.json_manager.data_dir / filename
                if file_path.exists():
                    try:
                        content = self.json_manager.load_json_content(content_type)
                        integrity_report["json_files"][content_type] = {
                            "exists": True,
                            "valid_json": content is not None,
                            "size": file_path.stat().st_size,
                        }
                    except Exception as e:
                        integrity_report["json_files"][content_type] = {
                            "exists": True,
                            "valid_json": False,
                            "error": str(e),
                        }
                else:
                    integrity_report["json_files"][content_type] = {
                        "exists": False,
                        "valid_json": False,
                    }

            # Determine overall status
            sqlite_ok = integrity_report["sqlite_integrity"]
            json_ok = all(
                f.get("valid_json", False)
                for f in integrity_report["json_files"].values()
            )

            if sqlite_ok and json_ok:
                integrity_report["overall_status"] = "healthy"
            elif sqlite_ok or json_ok:
                integrity_report["overall_status"] = "degraded"
            else:
                integrity_report["overall_status"] = "corrupted"

        except Exception as e:
            integrity_report["error"] = str(e)
            integrity_report["overall_status"] = "error"

        return integrity_report
